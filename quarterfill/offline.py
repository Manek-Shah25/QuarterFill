"""Read SEC Financial Statement Data Set TSVs without guessing fiscal contexts."""
from io import BytesIO
from zipfile import ZipFile
import pandas as pd


def import_fsn(content):
    """Return joined raw disclosure rows. Period/definition review precedes use as cells.

    Works with quarterly Financial Statement Data Sets containing sub/num/tag/pre.txt.
    Notes datasets with additional dimension tables are retained as a table bundle.
    No unsafe extraction to filesystem is performed.
    """
    with ZipFile(BytesIO(content)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 512 * 1024 * 1024:
            raise ValueError('Expanded dataset exceeds 512 MB; import a smaller subset offline.')
        tables={}
        for info in archive.infolist():
            name=info.filename.rsplit('/',1)[-1]
            if name.endswith('.txt'):
                tables[name[:-4]]=pd.read_csv(archive.open(info),sep='\t',dtype=str,keep_default_na=False)
    if not {'sub','num','tag'}.issubset(tables):
        raise ValueError('Expected SEC sub.txt, num.txt and tag.txt tables.')
    rows=tables['num'].merge(tables['sub'],on='adsh',how='left',suffixes=('','_submission'))
    rows=rows.merge(tables['tag'],on=['tag','version'],how='left',suffixes=('','_taxonomy'))
    return rows, tables
