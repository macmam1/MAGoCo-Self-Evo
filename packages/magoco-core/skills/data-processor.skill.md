---
name: data-processor
version: 1.0.0
description: "Advanced data processing utilities for CSV, JSON, and DataFrame operations"
category: utility
author: MAGoCo Team
license: MIT
tags: [data, processing, csv, json, pandas]

min_magoco_version: "0.3.0"
python_version: ">=3.10"

scope: global
source: local

entry_points:
  - name: transform_data
    description: "Transform data between formats (CSV, JSON, DataFrame)"
    handler: ":transform_data_handler"
    parameters:
      - name: input_format
        type: string
        description: "Input data format"
        required: true
        enum: ["csv", "json", "auto"]
      - name: output_format
        type: string
        description: "Output format"
        required: true
        enum: ["json", "csv", "summary"]
      - name: data
        type: string
        description: "Input data string"
        required: true
    returns: "string"

  - name: generate_summary
    description: "Generate a statistical summary of tabular data"
    handler: ":generate_summary_handler"
    parameters:
      - name: data
        type: string
        description: "Input data (CSV or JSON)"
        required: true
      - name: format
        type: string
        description: "Summary format"
        required: false
        default: "brief"
    returns: "object"

dependencies: []
---

# Data Processor Skill

This skill provides utilities for processing and summarizing tabular data.

## Features
- Transform CSV to JSON and back
- Generate statistical summaries
- Handle large datasets efficiently

## Usage

```bash
magoco skill exec data-processor transform_data
```

## Handlers

The handler functions are defined in the companion Python file (`data-processor.py`).
They provide the actual implementation for the entry points defined above.

```python
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
```
