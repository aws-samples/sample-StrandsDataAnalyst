STANDARD_FIELDS = {"name", "type", "distinct_values", "data_type"}


def format_example(example):
    if type(example) is str:
        return f'"{example}"'
    else:
        return str(example)


def format_table_field(field):
    description = []
    
    if field['type'] == 'INTEGER' and set(field['distinct_values']) == {0, 1}:
        description.append("BINARY-FLAG (0, 1)")
    else:
        description.append(f"Type {field['type']}")
        if len(field['distinct_values']) == 1:
           examples_description = f"Unique Value: {field['distinct_values'][0]}"
        else:
            examples = ', '.join([format_example(example) for example in field['distinct_values']])
            examples_description = f"Examples: {examples}"
        description.append(examples_description)

    for key, value in field.items():
        if key in STANDARD_FIELDS:
            continue
        description.append(f"{key}: {value}")

    return f"- {field['name']}: {'. '.join(description)}."


def format_db_schema(db_schema):
    formatted_db_schema = []
    for table, table_schema in db_schema.items():
        table_description = [f'#### Table Name: "{table}"']
        field_descriptions = "\n".join(format_table_field(field) for field in table_schema)
        table_description.append(f"## Column Descriptions:\n{field_descriptions}")
        formatted_db_schema.append('\n'.join(table_description))
    return '\n'.join(formatted_db_schema)
