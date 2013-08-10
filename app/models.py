from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.sql.expression import and_, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import CreateTable
from datetime import datetime
from __init__ import app

import uuid
import base62

db = SQLAlchemy(app)

def serialize(obj):
    import json
    if isinstance(obj.__class__, DeclarativeMeta):
        # an SQLAlchemy class
        fields = {}
        for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
            data = obj.__getattribute__(field)
            try:
                json.dumps(data) # this will fail on non-encodable values, like other classes
                fields[field] = data
            except TypeError:
                fields[field] = None
        # a json-encodable dict
        return fields


class TranslationRequest(db.Model):
    id = db.Column(UUID, primary_key=True)
    user_id = db.Column(UUID)
    timestamp = db.Column(db.DateTime(timezone=True))
    source = db.Column(db.String(16))
    target = db.Column(db.String(16))
    original_text = db.Column(db.Text)
    original_text_hash = db.Column(db.String(255))

    def serialize(self):
        # Synthesized property
        self.id_b62 = base62.encode(uuid.UUID(self.id).int)

        return serialize(self)

    @staticmethod
    def fetch(id_b62=None, original_text_hash=None, source=None, target=None):
        if id_b62 != None:
            translation_id = base62.decode(id_b62)
            return TranslationRequest.query.get(str(uuid.UUID(int=translation_id)))

        else:
            return TranslationRequest.query.filter_by(
                original_text_hash=original_text_hash,
                source=source, target=target).first()

    @staticmethod
    def insert(commit=True, **kwargs):
        treq = TranslationRequest(id=str(uuid.uuid4()))
        treq.timestamp = datetime.now()

        for key, value in kwargs.iteritems():
            setattr(treq, key, value);

        db.session.add(treq)
        if commit: db.session.commit()

        return treq


class TranslationResponse(db.Model):
    __table_args__ = ( db.UniqueConstraint('user_id', 'source', 'target', 'mode', 'original_text_hash'), )

    id = db.Column(UUID, primary_key=True)
    user_id = db.Column(UUID, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime(timezone=True))
    source = db.Column(db.String(16))
    target = db.Column(db.String(16))
    # mode
    # 1: regular translation
    # 2: better translation (use Japanese as an intermediate langauge)
    # 3: human translation
    mode = db.Column(db.Integer)
    original_text_hash = db.Column(db.String(255))
    intermediate_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)

    user = relationship('User')

    def serialize(self):
        # Synthesized property
        self.id_b62 = base62.encode(uuid.UUID(self.id).int)

        return serialize(self)

    @staticmethod
    def fetch(id_b62=None, original_text_hash=None, source=None, target=None, mode=None):
        if id_b62 != None:
            translation_id = base62.decode(id_b62)
            return TranslationResponse.query.get(str(uuid.UUID(int=translation_id)))

        else:
            return TranslationResponse.query.filter_by(
                original_text_hash=original_text_hash,
                source=source, target=target, mode=mode).first()

    @staticmethod
    def insert(commit=True, **kwargs):
        tresp = TranslationResponse(id=str(uuid.uuid4()))
        tresp.timestamp = datetime.now()

        for key, value in kwargs.iteritems():
            setattr(tresp, key, value);

        db.session.add(tresp)
        if commit: db.session.commit()

        return tresp

class Translation(db.Model):
    """
    CREATE VIEW translation AS
        SELECT tres.id, tres.user_id, tres.timestamp,
            tres.source, tres.target, tres.mode,
            treq.original_text, tres.original_text_hash, tres.intermediate_text,
            tres.translated_text, r.rating, r.count FROM translation_response AS tres
        LEFT JOIN translation_request AS treq ON
            tres.source = treq.source AND
            tres.target = treq.target AND
            tres.original_text_hash = treq.original_text_hash
        LEFT JOIN (SELECT translation_id, sum(rating) AS rating, count(id) AS count FROM rating GROUP BY translation_id) AS r ON
            r.translation_id = tres.id
    """
    id = db.Column(UUID, primary_key=True)
    user_id = db.Column(UUID, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime(timezone=True))
    source = db.Column(db.String(16))
    target = db.Column(db.String(16))
    mode = db.Column(db.Integer)
    original_text = db.Column(db.Text)
    original_text_hash = db.Column(db.String(255))
    intermediate_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)
    rating = db.Column(db.Integer)

    user = relationship('User')

    def serialize(self):
        # Synthesized property
        self.id_b62 = base62.encode(uuid.UUID(self.id).int)

        return serialize(self)

    # FIXME: This may be a cause for degraded performance 
    @property
    def plus_ratings(self):
        return Rating.query.filter_by(translation_id=self.id, rating=1).count()

    # FIXME: This may be a cause for degraded performance 
    @property
    def minus_ratings(self):
        return Rating.query.filter_by(translation_id=self.id, rating=-1).count()

    @staticmethod
    def fetch(id_b62=None, original_text_hash=None, source=None, target=None, mode=None):
        if id_b62 != None:
            translation_id = base62.decode(id_b62)
            return Translation.query.get(str(uuid.UUID(int=translation_id)))

        else:
            return Translation.query.filter_by(
                original_text_hash=original_text_hash,
                source=source, target=target, mode=mode).first()


class TranslationAccessLog(db.Model):
    """
    flag
    0001: Created: This flag is on upon creation of a TranslationResponse record
    0002:
    0004:
    ...
    """

    FLAG_CREATED = 1
    
    id = db.Column(UUID, primary_key=True)
    translation_id = db.Column(UUID)
    user_id = db.Column(UUID)
    timestamp = db.Column(db.DateTime(timezone=True))
    user_agent = db.Column(db.String(255))
    remote_address = db.Column(db.String(64))
    flag = db.Column(db.Integer, default=0)

    @staticmethod
    def insert(commit=True, **kwargs):
        record = TranslationAccessLog(id=str(uuid.uuid4()))
        record.timestamp = datetime.now()

        for key, value in kwargs.iteritems():
            setattr(record, key, value);

        db.session.add(record)
        if commit: db.session.commit()

        return record


class Rating(db.Model):
    __table_args__ = ( db.UniqueConstraint('translation_id', 'user_id'), )

    id = db.Column(UUID, primary_key=True)
    translation_id = db.Column(UUID)
    user_id = db.Column(UUID)
    timestamp = db.Column(db.DateTime(timezone=True))
    rating = db.Column(db.Integer)

    def serialize(self):
        return serialize(self)

    @staticmethod
    def insert(commit=True, **kwargs):
        rating = Rating(id=str(uuid.uuid4()))
        rating.timestamp = datetime.now()

        for key, value in kwargs.iteritems():
            setattr(rating, key, value);

        db.session.add(rating)
        if commit: db.session.commit()

        return rating


class User(db.Model, UserMixin):
    __table_args__ = ( db.UniqueConstraint('oauth_provider', 'oauth_id'), {} )

    id = db.Column(UUID, primary_key=True)

    oauth_provider = db.Column(db.String(255))
    oauth_id = db.Column(db.String(255), unique=True)
    oauth_username = db.Column(db.String(255))

    family_name = db.Column(db.String(255))
    given_name = db.Column(db.String(255))
    email = db.Column(db.String(255))

    gender = db.Column(db.String(6))
    locale = db.Column(db.String(16))

    def serialize(self):
        return serialize(self)

    @property
    def name(self):
        # FIXME: i18n
        return '{} {}'.format(self.given_name, self.family_name)

    @staticmethod
    def insert(**kwargs):
        user = User.query.filter_by(oauth_id=kwargs['oauth_id']).first()

        if user == None:
            user = User(id=str(uuid.uuid4()))
            #user.timestamp = datetime.now()

            for key, value in kwargs.iteritems():
                setattr(user, key, value);

            db.session.add(user)
            db.session.commit()

        return user


class GeoIP(db.Model):
    """The primary purpose of this table is to hold IP-geolocation pairs.
    The table name itself is pretty mucy self-explanatory."""

    __tablename__ = 'geoip'

    address = db.Column(db.String(40), primary_key=True) # We may hold IPv6 addresses as well
    timestamp = db.Column(db.DateTime(timezone=True))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


#
# Generating SQL from declarative model definitions:
#
#     print CreateTable(User.__table__).compile(db.engine)
#

if __name__ == '__main__':
    tables = (User, TranslationRequest, TranslationResponse, Rating, )
    for table in tables:
        print '{};'.format(CreateTable(table.__table__).compile(db.engine))
    
    #db.create_all(tables=[TranslationRequest, TranslationResponse,])