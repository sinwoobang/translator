import hashlib
import sys
import json
import time

import click
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError
from dateutil import parser as datetime_parser

import uuid64
from app.models import db


class Translation(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    source_lang = db.Column(db.String)
    target_lang = db.Column(db.String)
    hash = db.Column(db.String, unique=True)
    data = db.Column(JSON)



@click.group()
def cli():
    pass


@cli.command()
def create_db():
    db.metadata.create_all(db.engine, tables=[Translation.__table__])


@cli.command()
@click.argument('filename')
def import_data(filename):

    for line in open(filename):
        cols = line.split('\t')

        if len(cols) != 4:
            sys.stderr.write('{}\n'.format(line))
            continue

        timestamp = time.mktime(datetime_parser.parse(cols[2]).timetuple())
        translation = Translation(
            id=uuid64.issue(timestamp),
            source_lang=cols[0].strip(),
            target_lang=cols[1].strip(),
            hash=hashlib.sha1(cols[3].strip()).hexdigest(),
            data=json.loads(cols[3])
        )

        print('Processing data ({}, {}, {})'.format(translation.source_lang,
            translation.target_lang, timestamp))
        try:
            db.session.add(translation)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


if __name__ == '__main__':
    cli()
