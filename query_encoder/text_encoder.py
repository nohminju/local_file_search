import torch
import open_clip
import numpy as np
from typing import List, Union

class KoreanTextEncoder:
    def __init__(self, model_name: str = 'xlm-roberta-base-ViT-B-32', pretrained: str = 'laion5b_s13b_b90k'):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.model, _, _ = open_clip.create_model_and_transforms(
            model_name, 
            pretrained=pretrained
        )
        self.model.to(self.device)
        self.model.eval()
        
        self.tokenizer = open_clip.get_tokenizer(model_name)

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


if __name__ == "__main__":
    encoder = KoreanTextEncoder()
    sample_query = "보라색 배경의 축제 포스터"
    vector = encoder.encode_text(sample_query)
    print(f"Vector shape: {vector.shape}")
    print(f"Sample values: {vector[:5]}")