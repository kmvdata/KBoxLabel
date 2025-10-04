"""
包装werkzeug.local（支持协程和线程）和threading.local（支持线程）下的全局session
兼容flask app上下文，以及普通线程上下文
"""
import threading
import traceback

from sqlalchemy.orm import scoped_session

from src.common.god import cosmos
from src.common.god.business_exception import BusinessException
from src.common.god.common_error import CommonError
from src.common.god.logger import logger


class DB(object):

    @staticmethod
    def thread_session() -> scoped_session | None:
        # threading.local()每次都会重新生成新的变量
        session = cosmos.sessions.get(threading.get_ident())
        if session is None:
            logger.error('没有合适的线程安全session')
            logger.error(''.join(traceback.format_stack(limit=10)))
            raise BusinessException(CommonError.SESSION_ERROR)
        return session

    @staticmethod
    def close():
        session = cosmos.sessions.get(threading.get_ident())
        session.close()
        pass
