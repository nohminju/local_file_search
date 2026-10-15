import torch
import open_clip
import numpy as np
from typing import Sequence, Union

Vector = Sequence[float]

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

    def encode(self, query: str) -> Vector:
        tokens = self.tokenizer([query]).to(self.device)

        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        vector_array = text_features.cpu().numpy()[0]
        return vector_array.tolist()

    def encode_text(self, text: Union[str, list[str]], to_numpy: bool = True):
        if isinstance(text, str):
            res = self.encode(text)
            return np.array(res) if to_numpy else res
        
        tokens = self.tokenizer(text).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
        vector_array = text_features.cpu().numpy()
        return vector_array if to_numpy else vector_array.tolist()


if __name__ == "__main__":
    encoder = KoreanTextEncoder()
    sample_query = "보라색 배경의 축제 포스터"
    vector = encoder.encode(sample_query)
    print(f"Vector length: {len(vector)}")
    print(f"Sample values: {vector[:5]}")
