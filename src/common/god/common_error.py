import i18n


class CommonError(object):
    """
    枚举类型不允许继承- -b，只能用class去继承了
    说明:
    错误码用来区分需要不同处理方法的异常，如果处理方法相同，建议用同一错误码，不同的个性化错误详细信息(数组的第三个元素)
    core和admin系统的错误码变排时可以相同(但是不同的错误)，但是common的错误码需要和任何一个系统区分开
    [0]给前端程序用来判断, [1]元素更多的是给内部开发者看, [2]更多给外部用户看
    """
    CODE = 0
    SUCCESS = [0, "success", 'success']
    UNKNOWN_ERROR = [CODE + 10000, '未知错误', '']
    PARAMETER_ERROR = [CODE + 10002, 'PARAMETER_ERROR', '参数错误']
    NOT_FOUND_ERROR = [CODE + 10003, 'kanata.NOT_FOUNT_ERROR', '资源不存在']

    CORE_ERROR = [CODE + 20000, 'core错误', '']
    ADMIN_ERROR = [CODE + 20001, 'admin错误', '']
    SESSION_ERROR = [CODE + 20002, 'session错误', '']
    ACCOUNT_ASSET_CHANGE_ERROR = [CODE + 20013, '账户资产变更错误', '']
    SIGNUP_ERROR = [CODE + 20014, '注册失败', '']
