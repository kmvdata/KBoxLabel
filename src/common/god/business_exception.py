class BusinessException(RuntimeError):
    error_code: int = -1
    error_msg: str = ''
    error_more_msg: str = None

    # def __init__(self):
    #     pass

    # def __init__(self, code):
    #     self.code = code

    def __init__(self, error: list, more_msg: str = None):
        self.error_code = error[0]
        self.error_msg = error[1] if more_msg is None else more_msg

    def __str__(self):
        return '错误码: %d, 错误信息: %s %s' % (self.error_code, self.error_msg, self.error_more_msg)
