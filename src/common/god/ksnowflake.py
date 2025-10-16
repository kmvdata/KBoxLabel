import secrets  # 使用加密安全的随机数生成器 [[2]]
import threading
import time


class KSnowflake:
    """
    雪花算法实现类（动态随机 machine_id）
    64位ID组成结构：
    - 1位符号位（固定0）
    - 41位时间戳（毫秒级）
    - 10位随机 machine_id（0-1023）
    - 12位序列号（同一毫秒内的递增序号）
    """

    _CLS_EPOCH_: int = int(time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, 0)) * 1000)

    def __init__(self):
        self.sequence = 0  # 同一毫秒内的序列号
        self.last_timestamp = -1  # 上次生成ID的时间戳
        self.lock = threading.Lock()  # 线程锁保证原子操作

        # # 时间戳起始点（2020-01-01）
        # self.epoch = int(time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, 0)) * 1000)

    @classmethod
    def set_custom_epoch(cls, year: int, month: int, day: int):
        """设置时间戳起始点（自定义）"""
        cls._CLS_EPOCH_ = int(time.mktime((year, month, day, 0, 0, 0, 0, 0, 0)) * 1000)

    def _til_next_millis(self, last_timestamp):
        """等待下一毫秒"""
        timestamp = self._get_current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._get_current_timestamp()
        return timestamp

    @staticmethod
    def _get_current_timestamp():
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    def gen_kid(self) -> int:
        """生成唯一ID（包含随机machine_id）"""
        with self.lock:
            timestamp = self._get_current_timestamp()

            # 检测时间回拨
            if timestamp < self.last_timestamp:
                raise Exception(f"时钟回拨 {self.last_timestamp - timestamp} 毫秒")

            # 同一毫秒内序列号递增
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & 0xFFF  # 12位序列号最大值4095
                if self.sequence == 0:
                    # 当前毫秒序列号已满，等待下一毫秒
                    timestamp = self._til_next_millis(self.last_timestamp)
            else:
                # 不同毫秒重置序列号
                self.sequence = 0

            self.last_timestamp = timestamp

            # 动态生成随机 machine_id（0-1023，10位）
            machine_id = secrets.randbelow(1024) << 12  # 使用加密安全的随机数 [[2]]

            # 组装64位ID
            return (timestamp - self._CLS_EPOCH_) << 22 | machine_id | self.sequence


# 使用示例
if __name__ == "__main__":
    snowflake = KSnowflake()  # 无需初始化machine_id
    KSnowflake.set_custom_epoch(2025, 5, 20)
    last_ns = time.time_ns()
    uint64_max = (1 << 64) - 1  # 即 18446744073709551615
    my_set = set()
    for _ in range(100000):
        unique_id = snowflake.gen_kid()
        my_set.add(unique_id)
        if uint64_max - 1000 < unique_id:
            print("unique_in overflow uint64")
            break
        print(unique_id)
    print(f"{(time.time_ns() - last_ns) / 1_000_000}ms ==> {len(my_set)}")
