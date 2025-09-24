import base64


class StringUtil:
    @staticmethod
    def string_to_base64(case_txt: str) -> str:
        """
        将字符串转换为标准Base64格式
        1. 使用标准Base64编码
        2. 返回标准的Base64编码字符串（包含大小写字母）
        """
        # 将字符串编码为UTF-8字节
        byte_data = case_txt.encode('utf-8')
        # 使用标准Base64编码
        encoded_data = base64.b64encode(byte_data)
        # 将编码后的字节转换为字符串
        return encoded_data.decode('utf-8')

    @staticmethod
    def base64_to_string(b64_txt: str) -> str:
        """
        将Base64编码字符串解码回原始字符串
        1. 处理标准的Base64编码字符串
        2. 解码后返回原始文本
        """
        # 将Base64字符串编码为字节
        byte_data = b64_txt.encode('utf-8')
        # 使用标准Base64解码
        decoded_data = base64.b64decode(byte_data)
        # 将解码后的字节转换为字符串
        return decoded_data.decode('utf-8')


# 测试用例保持不变
def test_case(case_txt: str):
    b64_txt = StringUtil.string_to_base64(case_txt)
    ori_txt = StringUtil.base64_to_string(b64_txt)
    print(f'{case_txt}: {b64_txt} ---> {ori_txt}')


if __name__ == '__main__':
    test_case('123')  # 基础测试
    test_case('car')  # 混合大小写处理
    test_case('traffic light')  # 含空格和长文本
