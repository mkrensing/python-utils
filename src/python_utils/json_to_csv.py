import pandas
from cherrypicker import CherryPicker
import io
import string


def convert_json_to_csv(json):
    picker = CherryPicker(json)
    flat = picker.flatten().get()
    csv = pandas.DataFrame(flat).to_csv(index=False, sep=';', line_terminator='\n', decimal=',')

    return csv


def convert_json_to_excel_workbook(sheet_name, json):

    flat = convert_to_flat_json(json)
    return convert_flat_json_to_excel_workbook(flat, sheet_name)


def convert_to_flat_json(json):
    picker = CherryPicker(json)
    flat = picker.flatten().get()
    return flat


def convert_flat_json_to_excel_workbook(flatted_json, sheet_name):

    buffer = io.BytesIO()
    writer = pandas.ExcelWriter(buffer, engine='xlsxwriter')

    csvFrame = pandas.DataFrame(flatted_json)
    csvFrame.to_excel(writer, sheet_name=sheet_name)

    generate_excel_names_for_columns(writer, csvFrame, sheet_name)

    writer.close()
    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_names_for_columns(writer, csvFrame, sheet_name):

    range_names = ["ID"] + [col.upper() for col in csvFrame.columns]
    range_end = len(csvFrame) + 1
    excel_columns = string.ascii_uppercase[:len(range_names)]

    workbook = writer.book
    for (column_name, excel_column_id) in zip(range_names, excel_columns):
        workbook.define_name(f"{sheet_name}!{column_name}", f"={sheet_name}!${excel_column_id}$2:${excel_column_id}${range_end}")
