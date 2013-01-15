import time
import warnings
from . import StorageBase, StorageException
from .. import logger, LOG, inRecovery
from sqlalchemy import (Column, Integer, String,
                        create_engine, MetaData, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

Base = declarative_base()


class SimplePushSQL(Base):
    __tablename__ = 'simplepush'

    chid = Column('chid', String(25), primary_key=True, unique=True)
    uaid = Column('uaid', String(25), index=True)
    vers = Column('version', String(255), nullable=True)
    last = Column('last_accessed', Integer, index=True)
    state = Column('state', Integer, default=1)


class Storage(StorageBase):
    __database__ = 'simplepush'

    def __init__(self, config, **kw):
        try:
            super(Storage, self).__init__(config, **kw)
            self.metadata = MetaData()
            self._connect()
            #TODO: add the most common index.
        except Exception, e:
            logger.log(msg='Could not initialize Storage "%s"' % str(e),
                       type='error', severity=LOG.CRITICAL)
            raise e

    def _connect(self):
        try:
            userpass = ''
            host = ''
            if (self.settings.get('db.user')):
                userpass = '%s:%s@' % (self.settings.get('db.user'),
                                       self.settings.get('db.password'))
            if (self.settings.get('db.host')):
                host = '%s' % self.settings.get('db.host')
            dsn = '%s://%s%s/%s' % (self.settings.get('db.type', 'mysql'),
                                    userpass, host,
                                    self.settings.get('db.db',
                                                      self.__database__))
            self.engine = create_engine(dsn, pool_recycle=3600)
            Base.metadata.create_all(self.engine)
            self.Session = scoped_session(sessionmaker(bind=self.engine,
                                                       expire_on_commit=True))
            #self.metadata.create_all(self.engine)
        except Exception, e:
            logger.log(msg='Could not connect to db "%s"' % repr(e),
                       type='error', severity=LOG.EMERGENCY)
            raise e

    def health_check(self):
        try:
            healthy = True
            session = self.Session()
            import pdb; pdb.set_trace()
            sp = SimplePushSQL(chid='test', uaid='test',
                               vers=0, last=int(time.time()))
            session.commit()
            sp = self.session.query(SimplePushSQL).filter_by(chid='test')
            session.delete(sp)
        except Exception, e:
            warnings.warn(str(e))
            return False
        return healthy

    def update_chid(self, chid, vers, logger):
        if chid is None:
            return False
        session = self.Session()
        try:
            rec = session.query(SimplePushSQL).filter_by(chid=chid,
                                                         state=1).first()
            rec.vers = vers
            rec.last = int(time.time())
            session.commit()
        except Exception, e:
            import pdb; pdb.set_trace()
            logger.warn(str(e))
            return False
        return True

    def register_chids(self, uaid, pairs, logger):
        try:
            session = self.Session()
            for pair in pairs:
                session.add(SimplePushSQL(chid=pair['channelID'],
                                          uaid=uaid,
                                          vers=pair['version'],
                                          last=int(time.time())))
            session.commit()
        except Exception, e:
            import pdb; pdb.set_trace()
            logger.error(str(e))
            return False
        return True

    def register_chid(self, uaid, chid, logger):
        if chid is None or uaid is None:
            return False
        try:
            self.register_chids(uaid, [{'channelID': chid,
                                 'version': None}], logger)
        except Exception, e:
            import pdb; pdb.set_trace()
            logger.error(str(e))
            return False
        return True

    def delete_chid(self, uaid, chid, logger):
        if chid is None or uaid is None:
            return False
        try:
            session = self.Session()
            rec = session.query(SimplePushSQL).filter_by(chid=chid,
                                                         uaid=uaid).first()
            rec.state=0
            #rec.delete()
            session.commit()
        except Exception, e:
            import pdb; pdb.set_trace();
            logger.error(str(e))
            return False
        return True

    def get_updates(self, uaid, logger):
        if uaid is None:
            raise StorageException('No UserAgentID provided')
        try:
            session = self.Session()
            records = session.query(SimplePushSQL).filter_by(uaid=uaid)
            if records.count() == 0:
                return None
            digest = []
            updates = []
            expired = []
            for record in records:
                if record.state:
                    digest.append(record.chid)
                    updates.append({'channelID': record.chid,
                                    'version': record.vers})
                else:
                    expired.append(record.chid)
            return {'digest': ','.join(digest),
                    'updates': updates,
                    'expired': expired}
        except Exception, e:
            import pdb; pdb.set_trace();
            logger.error(str(e))
        return False

    def reload_data(self, uaid, data, logger):
        # Only allow if we're in recovery?
        if uaid is None:
            raise StorageException('No UserAgentID specified')
        if data is None or len(data) == 0:
            raise StorageException('No Data specified')
        try:
            session = self.Session()
            digest = []
            if session.query(SimplePushSQL).filter_by(uaid=uaid).count():
                return False
            for datum in data:
                session.add(SimplePushSQL(chid=datum.get('channelID'),
                                          uaid=uaid,
                                          vers=datum.get('version')))
                digest.append(datum.get('channelID'))
            session.commit()
            return ",".join(digest)
        except Exception, e:
            import pdb; pdb.set_trace();
            logger.error(str(e))
        return False

    def _get_record(self, chid):
        result = []
        try:
            session = self.Session()
            recs = session.query(SimplePushSQL).filter_by(chid=chid)
            for rec in recs:
                result.append(rec.__dict__)
            return result
        except Exception, e:
            import pdb; pdb.set_trace()
            logger.error(str(e))

    def purge(self):
        session = self.Session()
        sql = 'delete from simplepush;'
        self.engine.execute(text(sql))
        session.commit()
