class Qwen25VL72BInstruct:
    def __init__(self):
        self.model = "Qwen/Qwen2.5-VL-72B-Instruct"
        self.api_key = "16a177c8-8cec-4ea2-98ae-df25ba79e6ec"
        self.api_base = "https://api-inference.modelscope.cn/v1/"

class Qwen3_235B_A22B:
    def __init__(self):
        self.model = "Qwen/Qwen3-235B-A22B"
        self.api_key = "16a177c8-8cec-4ea2-98ae-df25ba79e6ec"
        self.api_base = "https://api-inference.modelscope.cn/v1/"

class GPT41:
    def __init__(self):
        self.model = "gpt-4.1"
        self.api_key = "sk-Tqg4hZnHUVngbD4iWrL9DqypUZyy7bTrwUQkDEgxLfCYzntg"
        self.api_base = "https://www.dmxapi.cn/v1"

class ModelConfigManager:
    """模型配置管理器，根据use_qwen参数和目标语言选择合适的模型"""
    
    @staticmethod
    def get_vision_model_config(use_qwen=True, target_language=""):
        """获取视觉模型配置
        Args:
            use_qwen: 是否使用Qwen模型
            target_language: 目标语言
        Returns:
            模型配置对象
        """
        # 检查是否为中文相关语言
        chinese_languages = ["Simplified Chinese", "Traditional Chinese (Taiwan)", "Traditional Chinese (Hong Kong)"]
        is_chinese = any(lang in target_language for lang in chinese_languages)
        
        if use_qwen and is_chinese:
            return Qwen25VL72BInstruct()
        else:
            return GPT41()
    
    @staticmethod
    def get_text_model_config(use_qwen=True, target_language=""):
        """获取文本模型配置
        Args:
            use_qwen: 是否使用Qwen模型
            target_language: 目标语言
        Returns:
            模型配置对象
        """
        # 检查是否为中文相关语言
        chinese_languages = ["Simplified Chinese", "Traditional Chinese (Taiwan)", "Traditional Chinese (Hong Kong)"]
        is_chinese = any(lang in target_language for lang in chinese_languages)
        
        if use_qwen and is_chinese:
            return Qwen3_235B_A22B()
        else:
            return GPT41()
    
    @staticmethod
    def supports_bounding_box(use_qwen=True, target_language=""):
        """检查当前配置是否支持边界框输出
        Args:
            use_qwen: 是否使用Qwen模型
            target_language: 目标语言
        Returns:
            bool: 是否支持边界框
        """
        # 只有Qwen模型支持边界框输出，GPT-4.1不支持
        chinese_languages = ["Simplified Chinese", "Traditional Chinese (Taiwan)", "Traditional Chinese (Hong Kong)"]
        is_chinese = any(lang in target_language for lang in chinese_languages)
        return use_qwen and is_chinese