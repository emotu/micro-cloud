import os
import json
import base64
import pprint
import tablib
# from app.config import settings


class ReportGen:
    def __init__(self, settings, report_dir=None):
        self.report_dir = report_dir if report_dir else settings.REPORTS_DIRECTORY

    # For multiple worksheets pass the datasets to DataBook like tablib.Databook((dataset1, dataset2))
    def prepare_data(cls, headers, *raw_data, **kwargs):
        # headers = ('first_name', 'last_name')
        # data = [('John', 'Adams'), ('George', 'Washington')]
        sheet_name = kwargs.get("sheet_name", None)
        if len(raw_data) > 0 and type(raw_data[0]) is dict:
            if sheet_name:
                data = tablib.Dataset(title=sheet_name)
            else:
                data = tablib.Dataset()
            data.dict = raw_data
        elif len(raw_data) > 0 and type(raw_data[0]) is tuple:
            if sheet_name:
                data = tablib.Dataset(*raw_data, headers=headers, title=sheet_name)
            else:
                data = tablib.Dataset(*raw_data, headers=headers)
        else:
            if sheet_name:
                data = tablib.Dataset(title=sheet_name)
            else:
                data = tablib.Dataset()

        return data

    def download_csv(self, filename, headers, *data):

        data = self.prepare_data(headers, *data)
        fullpath = "%s/%s.csv" % (self.report_dir, filename)
        with open(fullpath, 'wb') as f:
            f.write(data.csv)

        return data.csv

    def download_html(self, filename, headers, *data):
        data = self.prepare_data(headers, *data)
        return data.html

    def download_json(self, filename, headers, *data):
        data = self.prepare_data(headers, *data)
        fullpath = "%s/%s.json" % (self.report_dir, filename)
        with open(fullpath, 'wb') as f:
            f.write(data.json)
        return data.json

    def download_xlsx(self, filename, headers, *data, **kwargs):
        data = self.prepare_data(headers, *data, **kwargs)

        fullpath = "%s/%s.xlsx" % (self.report_dir, filename)
        with open(fullpath, 'wb') as f:
            f.write(data.xlsx)

        return data.xlsx

    def download_xls(self, filename, headers, *data, **kwargs):
        data = self.prepare_data(headers, *data, **kwargs)

        fullpath = "%s/%s.xls" % (self.report_dir, filename)
        with open(fullpath, 'wb') as f:
            f.write(data.xls)

        return data.xls

    def download_workbook(self, filename, data):
        book = tablib.Databook(data)
        fullpath = "%s/%s.xlsx" % (self.report_dir, filename)
        with open(fullpath, 'wb') as f:
            f.write(book.xlsx)

        return book.xlsx

    def prepare_excel_data(self, path):
        imported_data = tablib.Dataset().load(open(path).read())
        json_string = imported_data.export('json')
        json_data = json.loads(json_string)
        return json_data


async def convert_file_base64(source_file):
    """convert a file to its base64 equivalent"""

    filename = source_file.split('/')[-1]
    ext = filename.split('.')[-1]
    try:
        with open(source_file, "rb") as a_file:
            encoded_string = base64.b64encode(a_file.read()).decode("ascii")
    except Exception as e:
        print(e)
        return None
    return {'filename': filename, 'stream': encoded_string, 'ext': ext}