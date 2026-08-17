"""Data Processor Skill - Handlers for data-processor.skill.md"""

def transform_data_handler(input_format: str, output_format: str, data: str) -> str:
    """Transform data between formats."""
    import json
    import csv
    import io
    
    if input_format == "auto":
        input_format = "json" if data.strip().startswith("{") else "csv"
    
    if input_format == "csv":
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
    else:
        rows = json.loads(data) if isinstance(data, str) else data
    
    if output_format == "json":
        return json.dumps(rows, indent=2)
    elif output_format == "csv":
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    elif output_format == "summary":
        return _generate_summary(rows)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")

def generate_summary_handler(data: str, format: str = "brief") -> str:
    """Generate statistical summary."""
    import json
    import csv
    import io
    
    rows = json.loads(data) if isinstance(data, str) else data
    return _generate_summary(rows, format)

def _generate_summary(rows, format="brief"):
    if not rows:
        return "No data to summarize."
    
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except json.JSONDecodeError:
            reader = csv.DictReader(io.StringIO(rows))
            rows = list(reader)
    
    summary = {
        "total_rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "sample": rows[0] if rows else {},
    }
    return json.dumps(summary, indent=2)