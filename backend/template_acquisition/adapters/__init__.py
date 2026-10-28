from .guangdong import GuangdongAdapter
from .jiangsu import JiangsuAdapter
from .liaoning import LiaoningAdapter
from .zhejiang import ZhejiangAdapter

ADAPTERS = {
    "guangdong": GuangdongAdapter,
    "jiangsu": JiangsuAdapter,
    "liaoning": LiaoningAdapter,
    "zhejiang": ZhejiangAdapter,
}

__all__ = ["ADAPTERS", "GuangdongAdapter", "JiangsuAdapter", "LiaoningAdapter", "ZhejiangAdapter"]
