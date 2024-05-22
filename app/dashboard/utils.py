import pandas as pd

def convert_csv_to_utf8(file_path, encoding):
    """
    Convert csv to utf8
    """
    df = pd.read_csv(file_path, sep=',', encoding=encoding)
    df.to_csv(file_path, index=False, encoding='utf-8')