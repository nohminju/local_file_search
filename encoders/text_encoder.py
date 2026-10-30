import torch
import open_clip
import numpy as np
from typing import List, Union

class KoreanTextEncoder:
    """
    공통 OpenCLIP 모델을 전달받아 한국어 텍스트를 벡터로 변환하는 인코더
    """
    def __init__(
        self, 
        model=None, 
        tokenizer=None, 
        model_name: str = 'xlm-roberta-base-ViT-B-32', 
        pretrained: str = 'laion5b_s13b_b90k',
        device=None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # 외부에서 넘겨받은 공통 모델/토크나이저 사용 (없을 경우 직접 로딩)
        if model is not None and tokenizer is not None:
            self.model = model
            self.tokenizer = tokenizer
        else:
            self.model, _, _ = open_clip.create_model_and_transforms(
                model_name, 
                pretrained=pretrained,
                device=self.device
            )
            self.tokenizer = open_clip.get_tokenizer(model_name)
            
        self.model.eval()

    def encode_text(self, text: Union[str, List[str]], to_numpy: bool = True) -> Union[np.ndarray, List[float]]:
        if isinstance(text, str):
            text_list = [text]
            is_single = True
        else:
            text_list = text
            is_single = False

        tokens = self.tokenizer(text_list).to(self.device)

        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        vector_array = text_features.cpu().numpy()

        if is_single:
            vector_array = vector_array[0]

        if not to_numpy:
            return vector_array.tolist()
            
        return vector_array
