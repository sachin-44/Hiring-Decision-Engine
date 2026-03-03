import json
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from .models import HiringDecision, HiringCriteria, Candidate, CandidateValue
from .forms import RoleTitleForm, CriteriaFormSet, CandidateNameFormSet, CandidateValueForm
from .scoring import run_scoring, run_scoring_with_role


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_scoring_input(session):
    """
    Convert session data into the exact format run_scoring() expects.
    criteria list: [{'id', 'name', 'weight', 'is_cost', 'description'}, ...]
    candidates list: [{'id', 'name', 'values': {criteria_id: raw_value}}, ...]
    """
    criteria   = session.get('criteria', [])
    candidates = session.get('candidates', [])
    return criteria, candidates


# ── Step 1: Role title ────────────────────────────────────────────────────────

def step1_role(request):
    if request.method == 'POST':
        form = RoleTitleForm(request.POST)
        if form.is_valid():
            request.session['role_title'] = form.cleaned_data['role_title']
            request.session.modified = True
            route = request.POST.get('route', 'manual')
            if route == 'upload':
                return redirect('upload_csv')
            return redirect('step2_criteria')
    else:
        form = RoleTitleForm(initial={'role_title': request.session.get('role_title', '')})
    return render(request, 'decisions/step1_role.html', {'form': form, 'step': 1})


# ── Step 2: Criteria + weights ─────────────────────────────────────────────────

def step2_criteria(request):
    if not request.session.get('role_title'):
        return redirect('step1_role')

    if request.method == 'POST':
        formset = CriteriaFormSet(request.POST, prefix='cr')
        if formset.is_valid():
            criteria_data = []
            for i, f in enumerate(formset.forms):
                d = f.cleaned_data
                if d:
                    criteria_data.append({
                        'id':          i + 1,
                        'name':        d['name'],
                        'weight':      d['weight'],
                        'is_cost':     d.get('is_cost', False),
                        'description': d.get('description', ''),
                        'scale_min':   d.get('scale_min'),   # None if not set
                        'scale_max':   d.get('scale_max'),   # None if not set
                    })
            if len(criteria_data) < 2:
                messages.error(request, "Please add at least 2 criteria.")
            else:
                request.session['criteria'] = criteria_data
                request.session.modified = True
                return redirect('step3_candidates')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        saved = request.session.get('criteria', [])
        initial = [
            {'name': c['name'], 'weight': c['weight'],
             'is_cost': c['is_cost'], 'description': c.get('description', ''),
             'scale_min': c.get('scale_min'), 'scale_max': c.get('scale_max')}
            for c in saved
        ] if saved else [
            {'name': 'Salary',        'weight': 40},
            {'name': 'Experience',    'weight': 30},
            {'name': 'Test Score',    'weight': 30},
        ]
        formset = CriteriaFormSet(prefix='cr', initial=initial)

    return render(request, 'decisions/step2_criteria.html', {
        'formset': formset,
        'step':    2,
        'role':    request.session.get('role_title'),
    })


# ── Step 3: Candidate names ────────────────────────────────────────────────────

def step3_candidates(request):
    if not request.session.get('criteria'):
        return redirect('step2_criteria')

    error = None

    if request.method == 'POST':
        # Read directly from POST — do not rely on formset validation
        # which can silently drop JS-added rows beyond the initial count
        total = int(request.POST.get('ca-TOTAL_FORMS', 0))
        candidates_data = []
        for i in range(total):
            name = request.POST.get(f'ca-{i}-name', '').strip()
            if name:
                candidates_data.append({
                    'id':     len(candidates_data) + 1,
                    'name':   name,
                    'values': {},
                })

        if len(candidates_data) < 2:
            error = "Please add at least 2 candidates."
        else:
            request.session['candidates'] = candidates_data
            request.session.modified = True
            return redirect('step4_values')

    # Build display list for GET (or re-render after error)
    saved = request.session.get('candidates', [])
    candidate_names = [c['name'] for c in saved] if saved else ['', '']

    if error:
        messages.error(request, error)

    return render(request, 'decisions/step3_candidates.html', {
        'candidate_names': candidate_names,
        'step':            3,
        'role':            request.session.get('role_title'),
    })


# ── Step 4: Raw values per candidate ──────────────────────────────────────

def step4_values(request):
    criteria   = request.session.get('criteria')
    candidates = request.session.get('candidates')

    if not criteria or not candidates:
        return redirect('step3_candidates')

    forms_list = [
        CandidateValueForm(
            request.POST if request.method == 'POST' else None,
            prefix=f'cv_{c["id"]}',
            criteria_list=criteria,
            candidate_name=c['name'],
        )
        for c in candidates
    ]

    if request.method == 'POST':
        if all(f.is_valid() for f in forms_list):
            for i, f in enumerate(forms_list):
                candidates[i]['values'] = f.get_values(criteria)
            request.session['candidates'] = candidates
            request.session.modified = True
            return redirect('results')
        else:
            messages.error(request, "Please fill in all values for every candidate.")

    # Build per-candidate cards: each card has the candidate name + list of
    # (criteria_info, field, errors) rows — one entry per criteria.
    # This drives the new card-per-candidate layout in the template.
    candidate_cards = []
    for i, (cand, form) in enumerate(zip(candidates, forms_list)):
        rows = []
        for c in criteria:
            fname = f'c_{c["id"]}'
            try:
                field  = form[fname]
                errors = field.errors
            except KeyError:
                field  = ''
                errors = []
            rows.append({
                'criteria_name': c['name'],
                'weight':        c['weight'],
                'is_cost':       c.get('is_cost', False),
                'description':   c.get('description', ''),
                'field':         field,
                'errors':        errors,
            })
        candidate_cards.append({
            'number': i + 1,
            'name':   cand['name'],
            'rows':   rows,
        })

    return render(request, 'decisions/step4_values.html', {
        'candidate_cards': candidate_cards,
        'criteria':        criteria,
        'step':            4,
        'role':            request.session.get('role_title'),
    })


# ── Results ────────────────────────────────────────────────────────────────────

def results(request):
    criteria, candidates = _build_scoring_input(request.session)
    role = request.session.get('role_title', 'Hiring Decision')

    if not criteria or len(candidates) < 2:
        messages.error(request, "Not enough data. Please start from the beginning.")
        return redirect('step1_role')

    # Make sure all candidates have values
    for c in candidates:
        if not c.get('values'):
            return redirect('step4_values')

    result = run_scoring_with_role(criteria, candidates, role=role)
    if result is None:
        messages.error(request, "Scoring failed. Please check your inputs.")
        return redirect('step4_values')

    # Warn if a criteria dominated unexpectedly
    dominant = result['dominant_criteria']
    if dominant['delta'] > 15:
        messages.warning(
            request,
            f"'{dominant['name']}' drove {dominant['actual_pct']}% of the final score "
            f"but was only weighted at {dominant['stated_pct']}%. "
            f"It had more influence than intended."
        )

    return render(request, 'decisions/results.html', {
        'role':          role,
        'result':        result,
        'criteria':      criteria,
        'is_csv':        request.session.get('is_csv', False),
        'num_to_rank':   request.session.get('num_to_rank', None),
    })


# ── AJAX: recalculate with adjusted weights ────────────────────────────────────

@require_POST
def recalculate(request):
    try:
        body = json.loads(request.body)
        updated_weights = body.get('weights', {})
        criteria, candidates = _build_scoring_input(request.session)

        if not criteria or not candidates:
            return JsonResponse({'error': 'Session expired.'}, status=400)

        # Apply updated weights (keep as integers)
        modified = []
        for c in criteria:
            try:
                w = int(float(updated_weights.get(str(c['id']), c['weight'])))
                w = max(1, w)
            except (ValueError, TypeError):
                w = c['weight']
            modified.append({**c, 'weight': w})

        result = run_scoring(modified, candidates)
        if result is None:
            return JsonResponse({'error': 'Scoring failed.'}, status=400)

        return JsonResponse({
            'ranked': [
                {
                    'rank':           r['rank'],
                    'candidate_name': r['candidate_name'],
                    'total_pct':      r['total_pct'],
                }
                for r in result['ranked']
            ],
            'is_stable':        result['is_stable'],
            'stability_detail': result['stability_detail'],
            'score_gap':        result['score_gap'],
        })

    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


# ── Save to database ───────────────────────────────────────────────────────────

def save_decision(request):
    criteria, candidates = _build_scoring_input(request.session)
    role = request.session.get('role_title')

    if not all([criteria, candidates, role]):
        messages.error(request, "Nothing to save.")
        return redirect('results')

    decision = HiringDecision.objects.create(
        user=request.user if request.user.is_authenticated else None,
        role_title=role
    )

    criteria_map = {}
    for c in criteria:
        obj = HiringCriteria.objects.create(
            decision=decision, name=c['name'], weight=c['weight'],
            is_cost=c.get('is_cost', False),
            description=c.get('description', ''), order=c['id']
        )
        criteria_map[c['id']] = obj

    for cand in candidates:
        cand_obj = Candidate.objects.create(decision=decision, name=cand['name'])
        for cid, val in cand['values'].items():
            CandidateValue.objects.create(
                candidate=cand_obj,
                criteria=criteria_map[int(cid)],
                value=val
            )

    messages.success(request, f"Saved: {role}")
    return redirect('decision_detail', pk=decision.pk)


# ── History ────────────────────────────────────────────────────────────────────

def decision_list(request):
    decisions = HiringDecision.objects.prefetch_related('criteria', 'candidates').all()
    return render(request, 'decisions/decision_list.html', {'decisions': decisions})


def decision_detail(request, pk):
    decision = get_object_or_404(
        HiringDecision.objects.prefetch_related('criteria', 'candidates__values__criteria'),
        pk=pk
    )
    criteria = [
        {'id': c.id, 'name': c.name, 'weight': c.weight,
         'is_cost': c.is_cost, 'description': c.description}
        for c in decision.criteria.all()
    ]
    candidates = []
    for cand in decision.candidates.all():
        values = {v.criteria_id: v.value for v in cand.values.select_related('criteria')}
        candidates.append({'id': cand.id, 'name': cand.name, 'values': values})

    result = run_scoring(criteria, candidates)
    return render(request, 'decisions/results.html', {
        'role': decision.role_title, 'result': result,
        'criteria': criteria, 'saved': True, 'decision': decision,
    })


def start_over(request):
    for key in ['role_title', 'criteria', 'candidates', 'is_csv', 'num_to_rank']:
        request.session.pop(key, None)
    return redirect('step1_role')


# ── Step 4 grid helper (used by template) ─────────────────────────────────────
# The grid is: grid[criteria_index][candidate_index] = (field_html, error_html)
# Built in the view so the template only does simple loops.


# ── CSV / Excel Upload ─────────────────────────────────────────────────────────



def _parse_uploaded_file(f):
    """
    Parse a CSV or XLSX file.
    Returns (headers, rows) where:
      headers = list of column name strings
      rows    = list of dicts {header: value}
    Raises ValueError with a user-friendly message on failure.
    """
    name = f.name.lower()

    if name.endswith('.xlsx') or name.endswith('.xls'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(f, data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            if len(all_rows) < 2:
                raise ValueError("The spreadsheet must have at least a header row and one data row.")
            headers = [str(c).strip() if c is not None else '' for c in all_rows[0]]
            rows = []
            for raw in all_rows[1:]:
                row = {headers[i]: (raw[i] if i < len(raw) else None) for i in range(len(headers))}
                rows.append(row)
            return headers, rows
        except ImportError:
            raise ValueError("openpyxl is required to read Excel files. Run: pip install openpyxl")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Could not read Excel file: {e}")

    elif name.endswith('.csv'):
        content = f.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except Exception:
                raise ValueError("Could not decode the CSV file. Please save it as UTF-8 and try again.")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        rows = list(reader)
        if not rows:
            raise ValueError("The CSV file appears to be empty.")
        return list(headers), rows

    else:
        ext = name.rsplit('.', 1)[-1] if '.' in name else 'unknown'
        raise ValueError(
            f"Unsupported file format: .{ext}. "
            f"Please upload a .csv or .xlsx file."
        )


def _validate_csv_data(headers, rows):
    """
    Deep validation of parsed CSV data.
    Returns a dict:
      {
        'ok': bool,
        'errors': [str],          # blocking errors
        'warnings': [str],        # non-blocking issues
        'bad_cells': [            # per-cell details for error table
            {'row': int, 'col': str, 'value': str, 'issue': str}
        ],
        'preview_rows': [dict],   # first 5 rows for preview
        'stats': {'rows': int, 'cols': int, 'empty_cells': int}
      }
    """
    errors = []
    warnings = []
    bad_cells = []

    # ── Structural checks ──────────────────────────────────────────────────
    if len(headers) < 2:
        errors.append("File must have at least 2 columns: one for candidate names and at least one criteria column.")
        return {'ok': False, 'errors': errors, 'warnings': warnings, 'bad_cells': [], 'preview_rows': [], 'stats': {}}

    if len(rows) < 2:
        errors.append(f"File only has {len(rows)} data row(s). Need at least 2 candidates to compare.")
        return {'ok': False, 'errors': errors, 'warnings': warnings, 'bad_cells': [], 'preview_rows': [], 'stats': {}}

    # ── Empty header names ────────────────────────────────────────────────
    empty_header_cols = [i for i, h in enumerate(headers) if not h.strip()]
    if empty_header_cols:
        warnings.append(f"Column(s) {[i+1 for i in empty_header_cols]} have no header name and will be skipped.")

    # ── Duplicate headers ─────────────────────────────────────────────────
    seen_headers = {}
    for i, h in enumerate(headers):
        if h in seen_headers:
            errors.append(f"Duplicate column name '{h}' found (columns {seen_headers[h]+1} and {i+1}). Column names must be unique.")
        seen_headers[h] = i

    # ── Candidate name column checks ──────────────────────────────────────
    name_col = headers[0]
    empty_names = [i+2 for i, row in enumerate(rows) if not str(row.get(name_col, '') or '').strip()]
    if empty_names:
        if len(empty_names) <= 5:
            warnings.append(f"Row(s) {empty_names} have empty candidate names — will be labelled 'Candidate N' automatically.")
        else:
            warnings.append(f"{len(empty_names)} rows have empty candidate names — will be labelled automatically.")

    # Duplicate candidate names
    name_counts = {}
    for row in rows:
        n = str(row.get(name_col, '') or '').strip()
        if n:
            name_counts[n] = name_counts.get(n, 0) + 1
    dupes = [n for n, c in name_counts.items() if c > 1]
    if dupes:
        warnings.append(f"Duplicate candidate name(s): {', '.join(dupes[:5])}{'...' if len(dupes)>5 else ''}. Each will be scored separately.")

    # ── Per-cell numeric validation for criteria columns ──────────────────
    crit_headers = [h for h in headers[1:] if h.strip()]
    empty_cell_count = 0

    for row_idx, row in enumerate(rows):
        for h in crit_headers:
            val = row.get(h)
            val_str = str(val).strip() if val is not None else ''

            if val_str == '' or val_str.lower() in ('none', 'null', 'n/a', '-', 'na'):
                empty_cell_count += 1
                if len(bad_cells) < 20:  # cap at 20 for display
                    bad_cells.append({
                        'row': row_idx + 2,  # +2 = 1-based + header row
                        'col': h,
                        'value': val_str or '(empty)',
                        'issue': 'Missing value'
                    })
                continue

            # Check if numeric
            cleaned = val_str.replace(',', '').replace(' ', '')
            try:
                float(cleaned)
            except ValueError:
                if len(bad_cells) < 20:
                    bad_cells.append({
                        'row': row_idx + 2,
                        'col': h,
                        'value': val_str,
                        'issue': 'Not a number'
                    })

    # Summarise non-numeric errors
    non_numeric = [bc for bc in bad_cells if bc['issue'] == 'Not a number']
    missing = [bc for bc in bad_cells if bc['issue'] == 'Missing value']

    if non_numeric:
        cols_affected = list(dict.fromkeys(bc['col'] for bc in non_numeric))
        errors.append(
            f"Non-numeric values found in {len(non_numeric)} cell(s) across column(s): "
            f"{', '.join(cols_affected)}. All criteria columns must contain numbers."
        )

    if missing:
        if empty_cell_count > 10:
            warnings.append(
                f"{empty_cell_count} empty cell(s) detected. Missing values will be treated as 0."
            )
        else:
            cols_affected = list(dict.fromkeys(bc['col'] for bc in missing))
            warnings.append(
                f"{empty_cell_count} empty cell(s) in column(s): {', '.join(cols_affected)}. "
                f"Missing values will be treated as 0."
            )

    # ── File stats ────────────────────────────────────────────────────────
    stats = {
        'rows': len(rows),
        'cols': len(crit_headers),
        'empty_cells': empty_cell_count,
    }

    return {
        'ok': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'bad_cells': bad_cells,
        'preview_rows': rows[:5],
        'stats': stats,
    }


def upload_csv(request):
    """Step: Upload CSV or Excel file."""
    if not request.session.get('role_title'):
        return redirect('step1_role')

    validation = None
    headers = None

    if request.method == 'POST' and request.FILES.get('datafile'):
        f = request.FILES['datafile']
        try:
            headers, rows = _parse_uploaded_file(f)
            validation = _validate_csv_data(headers, rows)

            if validation['ok']:
                # Store raw parsed data in session for review step
                request.session['csv_headers'] = headers
                request.session['csv_rows'] = [
                    {k: str(v) if v is not None else '' for k, v in row.items()}
                    for row in rows
                ]
                request.session.modified = True
                return redirect('upload_review')
            # else fall through to show validation errors

        except ValueError as e:
            validation = {
                'ok': False,
                'errors': [str(e)],
                'warnings': [],
                'bad_cells': [],
                'preview_rows': [],
                'stats': {},
            }
        except Exception as e:
            validation = {
                'ok': False,
                'errors': [f"Could not read the file: {e}"],
                'warnings': [],
                'bad_cells': [],
                'preview_rows': [],
                'stats': {},
            }

    return render(request, 'decisions/upload_csv.html', {
        'role':       request.session.get('role_title'),
        'validation': validation,
        'headers':    headers,
    })


def _auto_detect_criteria(headers, rows):
    """
    Given column headers and data rows, build criteria list.
    - First column = candidate name column (skipped as criteria)
    - Remaining columns = criteria
    - is_cost auto-detected via scoring.py smart scale keywords
    - Default weight = 10 (user adjusts in review)
    """
    from .scoring import detect_smart_scale, _SMART_SCALES

    # Cost keywords — if column name matches, default is_cost=True
    COST_KEYWORDS = ['salary', 'ctc', 'package', 'compensation', 'cost',
                     'notice', 'notice period', 'price', 'fee', 'age']

    criteria = []
    for i, h in enumerate(headers[1:], start=1):  # skip first col (candidate name)
        if not h:
            continue
        smart = detect_smart_scale(h)
        is_cost = any(kw in h.lower() for kw in COST_KEYWORDS)
        scale_min = smart[0] if smart else None
        scale_max = smart[1] if smart else None

        criteria.append({
            'id':          i,
            'name':        h,
            'weight':      10,
            'is_cost':     is_cost,
            'description': '',
            'scale_min':   scale_min,
            'scale_max':   scale_max,
        })
    return criteria


def upload_review(request):
    """Review detected criteria, set weights & directions, then load into session."""
    if not request.session.get('role_title'):
        return redirect('step1_role')

    headers = request.session.get('csv_headers')
    rows    = request.session.get('csv_rows')

    if not headers or not rows:
        return redirect('upload_csv')

    name_col   = headers[0]
    crit_headers = headers[1:]

    if request.method == 'POST':
        # Read user-adjusted weights and directions
        criteria = []
        for i, h in enumerate(crit_headers, start=1):
            try:
                weight = max(1, int(float(request.POST.get(f'weight_{i}', 10))))
            except (ValueError, TypeError):
                weight = 10
            is_cost   = request.POST.get(f'is_cost_{i}') == '1'
            scale_min_raw = request.POST.get(f'scale_min_{i}', '').strip()
            scale_max_raw = request.POST.get(f'scale_max_{i}', '').strip()
            try:
                scale_min = float(scale_min_raw) if scale_min_raw else None
            except ValueError:
                scale_min = None
            try:
                scale_max = float(scale_max_raw) if scale_max_raw else None
            except ValueError:
                scale_max = None

            criteria.append({
                'id':          i,
                'name':        h,
                'weight':      weight,
                'is_cost':     is_cost,
                'description': '',
                'scale_min':   scale_min,
                'scale_max':   scale_max,
            })

        # Build candidates from CSV rows
        candidates = []
        for j, row in enumerate(rows):
            name = str(row.get(name_col, '')).strip() or f'Candidate {j+1}'
            values = {}
            for c in criteria:
                raw = str(row.get(c['name'], '') or '').replace(',', '').strip()
                try:
                    values[c['id']] = float(raw)
                except ValueError:
                    values[c['id']] = 0.0
            candidates.append({
                'id':     j + 1,
                'name':   name,
                'values': values,
            })

        if len(candidates) < 2:
            messages.error(request, "Need at least 2 candidates to score.")
            return redirect('upload_review')

        # Load into session — same format as manual flow
        request.session['criteria']    = criteria
        request.session['candidates']  = candidates
        request.session['is_csv']      = True
        try:
            num_to_rank = max(1, min(int(request.POST.get('num_to_rank', 1)), len(candidates)))
        except (ValueError, TypeError):
            num_to_rank = 1
        request.session['num_to_rank'] = num_to_rank
        # Clean up temp csv data
        request.session.pop('csv_headers', None)
        request.session.pop('csv_rows',    None)
        request.session.modified = True
        return redirect('results')

    # GET — build review data with auto-detected defaults
    auto_criteria = _auto_detect_criteria(headers, rows)
    auto_map = {c['name']: c for c in auto_criteria}

    # Build column previews (min, max, sample values)
    col_previews = {}
    for h in crit_headers:
        vals = []
        for row in rows:
            raw = str(row.get(h, '') or '').replace(',', '').strip()
            try:
                vals.append(float(raw))
            except ValueError:
                pass
        col_previews[h] = {
            'min':    min(vals) if vals else 0,
            'max':    max(vals) if vals else 0,
            'sample': vals[:3],
        }

    # Sample candidate names
    sample_names = [str(r.get(name_col, '')).strip() for r in rows[:5]]
    total_candidates = len(rows)

    return render(request, 'decisions/upload_review.html', {
        'role':             request.session.get('role_title'),
        'name_col':         name_col,
        'crit_headers':     crit_headers,
        'auto_map':         auto_map,
        'col_previews':     col_previews,
        'sample_names':     sample_names,
        'total_candidates': total_candidates,
    })


# ── Export: CSV of scored candidates ──────────────────────────────────────────

def export_csv(request):
    """Download scored candidates as CSV — top N if num_to_rank set, else all."""
    criteria, candidates = _build_scoring_input(request.session)
    role = request.session.get('role_title', 'hiring')
    num_to_rank = request.session.get('num_to_rank', None)

    if not criteria or len(candidates) < 2:
        return redirect('results')

    result = run_scoring_with_role(criteria, candidates, role=role)
    if result is None:
        return redirect('results')

    ranked = result['ranked']
    if num_to_rank:
        export_rows = [r for r in ranked if ranked.index(r) < num_to_rank]
    else:
        export_rows = ranked

    response = HttpResponse(content_type='text/csv')
    safe_role = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in role).strip().replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{safe_role}_shortlist.csv"'

    writer_csv = csv.writer(response)

    # Header row
    header = ['Rank', 'Candidate Name', 'Total Score (%)']
    for c in criteria:
        header.append(f"{c['name']} (raw)")
        header.append(f"{c['name']} (pts)")
    writer_csv.writerow(header)

    # Data rows
    for r in export_rows:
        row = [r['rank'], r['candidate_name'], r['total_pct']]
        for c in criteria:
            raw = r['raw_values'].get(c['id'], '')
            pts = round(r['breakdown'].get(c['id'], 0), 3)
            row.extend([raw, pts])
        writer_csv.writerow(row)

    return response


# ── Export: PDF results report ────────────────────────────────────────────────


def export_pdf(request):
    """Generate a clean, well-aligned PDF results report using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO
    import datetime

    criteria, candidates = _build_scoring_input(request.session)
    role        = request.session.get('role_title', 'Hiring Decision')
    num_to_rank = request.session.get('num_to_rank', None)
    is_csv      = request.session.get('is_csv', False)

    if not criteria or len(candidates) < 2:
        return redirect('results')

    result = run_scoring_with_role(criteria, candidates, role=role)
    if result is None:
        return redirect('results')

    ranked    = result['ranked']
    narrative = result.get('narrative', {})
    today     = datetime.date.today().strftime('%d %b %Y')
    n_cands   = len(ranked)
    shortlist_n = num_to_rank if num_to_rank else 1

    # ── Colours ───────────────────────────────────────────────────────────
    NAVY    = colors.HexColor('#1A3A6E')
    NAVY2   = colors.HexColor('#2563eb')
    GREEN   = colors.HexColor('#166534')
    GREEN_L = colors.HexColor('#dcfce7')
    AMBER   = colors.HexColor('#d97706')
    AMBER_L = colors.HexColor('#fef3c7')
    GREY    = colors.HexColor('#f8f9fa')
    GREY2   = colors.HexColor('#e9ecef')
    BORDER  = colors.HexColor('#dee2e6')
    WHITE   = colors.white
    TEXT    = colors.HexColor('#1f2937')
    MUTED   = colors.HexColor('#6b7280')

    # ── Document ──────────────────────────────────────────────────────────
    buffer = BytesIO()
    PAGE_W, PAGE_H = A4
    LM = RM = 1.8 * cm
    TM = 1.5 * cm
    BM = 1.8 * cm
    W = PAGE_W - LM - RM  # 17.4 cm usable
    BOX_PAD = 18  # winner_box left+right inner padding (points each side)
    IW = W - BOX_PAD * 2  # inner usable width inside padded winner box

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM, bottomMargin=BM,
        title=f"Hiring Scorecard — {role}",
    )

    # ── Base styles ───────────────────────────────────────────────────────
    SS = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=SS['Normal'], **kw)

    s_white_title = S('WT', fontSize=20, textColor=WHITE, fontName='Helvetica-Bold', leading=24)
    s_white_sub   = S('WS', fontSize=9,  textColor=colors.HexColor('#93c5fd'), fontName='Helvetica', leading=13)
    s_white_muted = S('WM', fontSize=8.5, textColor=colors.HexColor('#bfdbfe'), fontName='Helvetica')
    s_h1  = S('H1', fontSize=13, textColor=NAVY, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=7, leading=16)
    s_h2  = S('H2', fontSize=10, textColor=NAVY, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4, leading=13)
    s_body = S('BD', fontSize=9.5, textColor=TEXT, leading=15, spaceAfter=6)
    s_sm  = S('SM', fontSize=8,   textColor=MUTED, leading=11)
    s_tbl_hdr = S('TH', fontSize=8, textColor=WHITE, fontName='Helvetica-Bold', leading=10, alignment=TA_CENTER)
    s_tbl_hdr_l = S('THL', fontSize=8, textColor=WHITE, fontName='Helvetica-Bold', leading=10)
    s_tbl_c   = S('TC', fontSize=8.5, textColor=TEXT, leading=11, alignment=TA_CENTER)
    s_tbl_l   = S('TL', fontSize=8.5, textColor=TEXT, leading=11)
    s_tbl_b   = S('TB', fontSize=8.5, textColor=TEXT, leading=11, fontName='Helvetica-Bold')
    s_stat_v  = S('SV', fontSize=18, textColor=NAVY, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=22)
    s_stat_l  = S('SL', fontSize=7.5, textColor=MUTED, alignment=TA_CENTER, leading=10)

    story = []

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 1: HEADER BANNER
    # ─────────────────────────────────────────────────────────────────────
    banner = Table(
        [[Paragraph(f"Hiring Scorecard", s_white_title),
          Paragraph(f"Generated {today}", S('GD', fontSize=8.5, textColor=colors.HexColor('#93c5fd'), alignment=TA_RIGHT, leading=11))]],
        colWidths=[W * 0.7, W * 0.3]
    )
    banner.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), NAVY),
        ('TOPPADDING',  (0,0), (-1,-1), 16),
        ('BOTTOMPADDING',(0,0),(-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 18),
        ('RIGHTPADDING',(0,0), (-1,-1), 18),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(banner)

    # Role subtitle strip
    role_strip = Table(
        [[Paragraph(role, S('RL', fontSize=11, textColor=colors.HexColor('#93c5fd'), fontName='Helvetica', leading=14))]],
        colWidths=[W]
    )
    role_strip.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), NAVY),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 14),
        ('LEFTPADDING',  (0,0), (-1,-1), 18),
        ('RIGHTPADDING', (0,0), (-1,-1), 18),
    ]))
    story.append(role_strip)
    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 2: STAT CARDS
    # ─────────────────────────────────────────────────────────────────────
    winner = ranked[0]
    stats = [
        (str(n_cands),         'Candidates'),
        (str(len(criteria)),   'Criteria'),
        (f"{winner['total_pct']}%", 'Top Score'),
        (str(shortlist_n),     'Positions'),
    ]
    stat_cells = []
    for val, lbl in stats:
        cell = Table(
            [[Paragraph(val, s_stat_v)],
             [Paragraph(lbl, s_stat_l)]],
            colWidths=[W/4 - 4]
        )
        cell.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), GREY),
            ('BOX',          (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING',   (0,0), (-1,-1), 10),
            ('BOTTOMPADDING',(0,0), (-1,-1), 10),
            ('LEFTPADDING',  (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ]))
        stat_cells.append(cell)
    stats_row = Table([stat_cells], colWidths=[W/4]*4)
    stats_row.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(stats_row)
    story.append(Spacer(1, 16))

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 3: WINNER / SHORTLIST BOX
    # ─────────────────────────────────────────────────────────────────────
    if shortlist_n == 1:
        # Single winner — clean two-column layout
        winner_inner = Table(
            [[Paragraph(winner['candidate_name'],
                        S('WN', fontSize=20, textColor=WHITE, fontName='Helvetica-Bold', leading=24)),
              Paragraph(f"{winner['total_pct']}%",
                        S('WP', fontSize=28, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=32))],
             [Paragraph('No. 1 Ranked Candidate — highest weighted score across all criteria',
                        s_white_muted),
              Paragraph(f"of {n_cands} candidates",
                        S('WC', fontSize=8.5, textColor=colors.HexColor('#bfdbfe'), alignment=TA_RIGHT, leading=11))]],
            colWidths=[IW * 0.70, IW * 0.30]
        )
        winner_inner.setStyle(TableStyle([
            ('TOPPADDING',   (0,0), (-1,-1), 5),
            ('BOTTOMPADDING',(0,0), (-1,-1), 5),
            ('LEFTPADDING',  (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ]))
    else:
        # Multi-shortlist — numbered list
        pill_rows = []
        for i, r in enumerate(ranked[:shortlist_n]):
            rank_label = str(i+1)
            name_style = S(f'PN{i}', fontSize=10 if i==0 else 9,
                           textColor=WHITE, fontName='Helvetica-Bold' if i==0 else 'Helvetica',
                           leading=13)
            score_style = S(f'PS{i}', fontSize=9, textColor=colors.HexColor('#93c5fd'),
                            alignment=TA_RIGHT, leading=13)
            pill_rows.append([
                Paragraph(rank_label, S(f'PR{i}', fontSize=8.5, textColor=NAVY if i==0 else WHITE,
                                        fontName='Helvetica-Bold', alignment=TA_CENTER, leading=12)),
                Paragraph(r['candidate_name'], name_style),
                Paragraph(f"{r['total_pct']}%", score_style),
            ])
        # Build alternating row backgrounds for shortlist — dark/slightly-darker navy rows
        SL_DARK  = colors.HexColor('#1A3A6E')   # primary navy
        SL_ALT   = colors.HexColor('#1e4080')   # slightly lighter navy for alternating
        shortlist_tbl = Table(pill_rows, colWidths=[0.9*cm, IW - 0.9*cm - 2.2*cm, 2.2*cm])
        sl_style = [
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 5),
            ('RIGHTPADDING',  (0,0), (-1,-1), 5),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW',     (0,0), (-1,-2), 0.3, colors.HexColor('#2d5099')),
        ]
        for si in range(shortlist_n):
            row_bg = SL_ALT if si % 2 else SL_DARK
            sl_style.append(('BACKGROUND', (0, si), (-1, si), row_bg))
            # Gold badge only on rank column #1, subtle circle elsewhere
            if si == 0:
                sl_style.append(('BACKGROUND', (0, si), (0, si), colors.HexColor('#f59e0b')))
                sl_style.append(('TEXTCOLOR',  (0, si), (0, si), NAVY))
            else:
                sl_style.append(('BACKGROUND', (0, si), (0, si), colors.HexColor('#2d5099')))
                sl_style.append(('TEXTCOLOR',  (0, si), (0, si), WHITE))
        shortlist_tbl.setStyle(TableStyle(sl_style))
        # Shortlist header line
        sl_header = Table(
            [[Paragraph(f"TOP {shortlist_n} SHORTLISTED",
                        S('SH', fontSize=7.5, textColor=colors.HexColor('#93c5fd'), fontName='Helvetica-Bold',
                          leading=10)),
              Paragraph(f"from {n_cands} candidates",
                        S('SF', fontSize=8, textColor=colors.HexColor('#bfdbfe'), alignment=TA_RIGHT, leading=10))]],
            colWidths=[IW * 0.55, IW * 0.45]
        )
        sl_header.setStyle(TableStyle([
            ('TOPPADDING',   (0,0), (-1,-1), 0),
            ('BOTTOMPADDING',(0,0), (-1,-1), 8),
            ('LEFTPADDING',  (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        winner_inner = Table(
            [[sl_header],
             [shortlist_tbl]],
            colWidths=[IW]
        )
        winner_inner.setStyle(TableStyle([
            ('TOPPADDING',   (0,0), (-1,-1), 0),
            ('BOTTOMPADDING',(0,0), (-1,-1), 0),
            ('LEFTPADDING',  (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))

    winner_box = Table([[winner_inner]], colWidths=[W])
    winner_box.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), NAVY),
        ('TOPPADDING',   (0,0), (-1,-1), 16),
        ('BOTTOMPADDING',(0,0), (-1,-1), 16),
        ('LEFTPADDING',  (0,0), (-1,-1), 18),
        ('RIGHTPADDING', (0,0), (-1,-1), 18),
        ('BOX',          (0,0), (-1,-1), 0, NAVY),
    ]))
    story.append(winner_box)
    story.append(Spacer(1, 20))

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 4: RANKING TABLE
    # (Show shortlist + up to 14 more, max 40 total to avoid 10-page PDFs)
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Candidate Ranking", s_h1))

    show_n = min(shortlist_n + 14, 40, n_cands)
    if n_cands > show_n:
        story.append(Paragraph(f"Showing top {show_n} of {n_cands} candidates.", s_sm))
        story.append(Spacer(1, 4))

    # Column widths: Rank | Candidate | Score | Bar (progress) | Status
    CW = [1.1*cm, W*0.36, 1.5*cm, W*0.28, 1.8*cm]

    rank_hdr = [
        Paragraph('#', s_tbl_hdr),
        Paragraph('Candidate', s_tbl_hdr_l),
        Paragraph('Score', s_tbl_hdr),
        Paragraph('Progress', s_tbl_hdr),
        Paragraph('Status', s_tbl_hdr),
    ]
    rank_rows = [rank_hdr]
    rank_style = [
        ('BACKGROUND',    (0,0), (-1,0), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('RIGHTPADDING',  (0,0), (-1,-1), 5),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',          (0,0), (-1,-1), 0.25, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY]),
    ]

    # Separator row after shortlist
    sep_row_idx = None

    for i, r in enumerate(ranked[:show_n]):
        is_short = i < shortlist_n
        rank_str = str(r['rank'])
        pct = r['total_pct']

        # Progress bar drawing — width must exactly match column width minus padding
        bar_w = float(CW[3]) - 10.0
        bar_h = 8.0
        d = Drawing(bar_w, bar_h + 4)
        d.add(Rect(0, 2, bar_w, bar_h, fillColor=GREY2, strokeColor=None, rx=2, ry=2))
        fill_pct = max(0.02, min(1.0, (pct - 50.0) / 50.0))
        fill_w = max(4.0, bar_w * fill_pct)
        fill_clr = GREEN if is_short else (NAVY2 if i == 0 else BORDER)
        d.add(Rect(0, 2, fill_w, bar_h, fillColor=fill_clr, strokeColor=None, rx=2, ry=2))

        status_p = Paragraph(
            'Shortlisted' if is_short else '',
            S(f'ST{i}', fontSize=7.5,
              textColor=GREEN if is_short else MUTED,
              fontName='Helvetica-Bold' if is_short else 'Helvetica',
              alignment=TA_CENTER, leading=10)
        )
        name_fn = 'Helvetica-Bold' if i == 0 else 'Helvetica'
        row = [
            Paragraph(rank_str, S(f'RK{i}', fontSize=9, alignment=TA_CENTER,
                                   fontName='Helvetica-Bold', leading=11,
                                   textColor=GREEN if is_short else NAVY)),
            Paragraph(r['candidate_name'], S(f'CN{i}', fontSize=9, fontName=name_fn, leading=11)),
            Paragraph(f"{pct}%", S(f'SC{i}', fontSize=9, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER, leading=11, textColor=NAVY)),
            d,
            status_p,
        ]
        rank_rows.append(row)
        ri = len(rank_rows) - 1

        if is_short:
            rank_style.append(('BACKGROUND', (0, ri), (-1, ri), colors.HexColor('#f0fdf4')))
        if i == shortlist_n - 1 and shortlist_n < show_n:
            sep_row_idx = ri

    rank_tbl = Table(rank_rows, colWidths=CW, repeatRows=1)
    rank_tbl.setStyle(TableStyle(rank_style))

    if sep_row_idx:
        # Insert separator after shortlist by adding a thick bottom border
        rank_tbl.setStyle(TableStyle([
            ('LINEBELOW', (0, sep_row_idx), (-1, sep_row_idx), 1.5, colors.HexColor('#86efac')),
        ]))

    story.append(rank_tbl)

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 5: WRITTEN ANALYSIS
    # ─────────────────────────────────────────────────────────────────────
    if narrative:
        story.append(Spacer(1, 18))
        story.append(HRFlowable(width=W, thickness=0.5, color=BORDER))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Decision Report", s_h1))

        sections = [
            ('Recommendation',          narrative.get('recommendation', '')),
            ('What Drove This Decision', narrative.get('decision_drivers', '')),
            ('Priority Alignment',       narrative.get('blindspot_analysis', '')),
            ('Confidence Assessment',    narrative.get('confidence_assessment', '')),
        ]
        if not is_csv and narrative.get('candidate_comparison'):
            sections.insert(2, ('Candidate Comparison', narrative['candidate_comparison']))

        for sec_title, sec_body in sections:
            if not sec_body:
                continue
            # Strip emoji from section titles for PDF
            clean_title = sec_title
            story.append(KeepTogether([
                Paragraph(clean_title, s_h2),
                Paragraph(sec_body.replace('₹', 'Rs.'), s_body),
            ]))

    # ─────────────────────────────────────────────────────────────────────
    # PAGE BREAK + SCORE BREAKDOWN
    # ─────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Score Breakdown by Criteria", s_h1))
    story.append(Paragraph(
        "Raw value and points contributed per candidate per criteria. "
        "Colour coding: dark green = excellent, green = good, amber = average, red = below average.",
        s_sm
    ))
    story.append(Spacer(1, 10))

    # Which candidates to show in breakdown
    bd_cands = ranked[:shortlist_n]
    n_bd = len(bd_cands)

    if n_bd > 8:
        # Too many for one table — split into groups of 8
        groups = [bd_cands[i:i+8] for i in range(0, n_bd, 8)]
    else:
        groups = [bd_cands]

    for g_idx, group in enumerate(groups):
        n_g = len(group)
        if g_idx > 0:
            story.append(Spacer(1, 10))

        # Fixed column widths: criteria name | weight | N candidate columns
        CRIT_W  = 3.8 * cm
        WT_W    = 0.8 * cm
        cand_w  = (W - CRIT_W - WT_W) / n_g

        # Header row
        bd_hdr = [
            Paragraph('Criteria', s_tbl_hdr_l),
            Paragraph('Wt.', S('WH', fontSize=7.5, textColor=WHITE, fontName='Helvetica-Bold',
                                alignment=TA_CENTER, leading=10)),
        ]
        for r in group:
            # Truncate long names for header
            name = r['candidate_name']
            if len(name) > 14:
                name = name[:12] + '..'
            bd_hdr.append(Paragraph(name,
                S(f'BH{r["rank"]}', fontSize=7.5, textColor=WHITE,
                  fontName='Helvetica-Bold', alignment=TA_CENTER, leading=10)))

        bd_rows = [bd_hdr]
        bd_style = [
            ('BACKGROUND',    (0,0), (-1,0), NAVY),
            ('BACKGROUND',    (0,-1), (-1,-1), NAVY),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 5),
            ('RIGHTPADDING',  (0,0), (-1,-1), 5),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('GRID',          (0,0), (-1,-1), 0.25, BORDER),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, GREY]),
        ]

        for c in criteria:
            row = [
                Paragraph(c['name'].replace('\u20b9','Rs.').replace('(\u20b9)','(Rs.)'),
                          S(f'CN{c["id"]}', fontSize=8.5, textColor=TEXT, leading=11)),
                Paragraph(str(c['weight']),
                          S(f'CW{c["id"]}', fontSize=8.5, textColor=NAVY, fontName='Helvetica-Bold',
                            alignment=TA_CENTER, leading=11)),
            ]
            for r in group:
                cid = c['id']
                raw = r['raw_values'].get(cid, r['raw_values'].get(str(cid), ''))
                pts = round(r['breakdown'].get(cid, r['breakdown'].get(str(cid), 0)), 3)
                nv  = r['norm_values'].get(cid, r['norm_values'].get(str(cid), 0))
                # Background colour by performance
                if nv >= 0.75:
                    bg = colors.HexColor('#d1fae5')
                elif nv >= 0.5:
                    bg = colors.HexColor('#ecfdf5')
                elif nv >= 0.3:
                    bg = colors.HexColor('#fef9c3')
                else:
                    bg = colors.HexColor('#fee2e2')

                raw_display = str(raw).replace('\u20b9', 'Rs.')
                cell_p = Paragraph(
                    f"<b>{raw_display}</b><br/><font size='6.5' color='#6b7280'>+{pts}pts</font>",
                    S(f'BP{c["id"]}{r["rank"]}', fontSize=8.5, alignment=TA_CENTER, leading=12)
                )
                row.append(cell_p)
                # We'll apply bg via style after
            bd_rows.append(row)

        # Total row
        total_row = [
            Paragraph('TOTAL', S('TOT', fontSize=8, textColor=WHITE, fontName='Helvetica-Bold', leading=10)),
            Paragraph('',      S('TW',  fontSize=8, textColor=WHITE, leading=10)),
        ]
        for r in group:
            total_row.append(Paragraph(
                f"<b>{r['total_pct']}%</b>",
                S(f'TP{r["rank"]}', fontSize=10, textColor=WHITE, fontName='Helvetica-Bold',
                  alignment=TA_CENTER, leading=13)
            ))
        bd_rows.append(total_row)

        # Apply per-cell background colours
        for row_i, c in enumerate(criteria):
            for col_i, r in enumerate(group):
                nv = r['norm_values'].get(c['id'], 0)
                if nv >= 0.75:
                    bg = colors.HexColor('#d1fae5')
                elif nv >= 0.5:
                    bg = colors.HexColor('#ecfdf5')
                elif nv >= 0.3:
                    bg = colors.HexColor('#fef9c3')
                else:
                    bg = colors.HexColor('#fee2e2')
                tbl_row = row_i + 1  # +1 for header
                tbl_col = col_i + 2  # +2 for criteria + weight cols
                bd_style.append(('BACKGROUND', (tbl_col, tbl_row), (tbl_col, tbl_row), bg))

        bd_tbl = Table(bd_rows, colWidths=[CRIT_W, WT_W] + [cand_w]*n_g, repeatRows=1)
        bd_tbl.setStyle(TableStyle(bd_style))
        story.append(bd_tbl)

    # ─────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Generated by HireIQ  |  {today}  |  "
        f"Scores are weighted multi-criteria rankings and should be used alongside human judgement.",
        s_sm
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    safe_role = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in role).strip().replace(' ', '_')
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{safe_role}_results.pdf"'
    return response
