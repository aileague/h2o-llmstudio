import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch

from llm_studio.src.datasets.text_causal_language_modeling_ds import (
    CustomDataset as LLMCustomDataset,
)

logger = logging.getLogger(__name__)


class CustomDataset(LLMCustomDataset):
    """
    Dataset for DPO optimization.
    The data is assumed to be in hierarchical form of the following format:

    Beginning of a chat-answer interaction (parent_id is not set):
        instruction                    What kind of noises did dinosaurs make?
        output               Humans and dinosaurs didn’t live at the same t...
        id                                610e4ad5-09c4-4055-9ff4-948fe6b4f832
        parent_id                                                         None
        chosen_response                                                   None
        rejected_response                                                 None

    Within a chat-answer interaction (parent_id points for the previous prompt-answer sample):
        instruction                                               yes they did
        output               to guess, and that would probably require lots...
        id                                573e8d77-550a-4889-8ff4-1e8d8944897c
        parent_id                         610e4ad5-09c4-4055-9ff4-948fe6b4f832
        chosen_response                                                   None
        rejected_response                                                 None


    Last question. Output should be empty, chosen and rejected responses should be given:
        instruction          Do have a phone number or email address for hi...
        output
        id                                e0edeaf1-166d-4683-8609-dcba6fafc520
        parent_id                         e7e96d54-006d-4b34-a9ed-479c3ec3068c
        chosen_response       He doesn’t have a publicly available phone nu...
        rejected_response     If you want to contact Ryan Reynolds by phone...
    """

    def __init__(self, df: pd.DataFrame, cfg: Any, mode: str = "train"):
        """
        Args:
            df: input DataFrame
            cfg: config with all the hyperparameters
            mode: dataset mode. One of {"train", "validation"}
        """
        assert (
            cfg.dataset.limit_chained_samples
        ), "Need to enable limit_chained_samples for dpo training"

        super().__init__(df=df, cfg=cfg, mode=mode)
        self.chosen_answers = (
            self.df[self.cfg.dataset.chosen_response_column].astype(str).values.tolist()
        )
        self.rejected_answer = (
            self.df[self.cfg.dataset.rejected_response_column]
            .astype(str)
            .values.tolist()
        )

    def __getitem__(self, idx: int) -> Dict:
        """Reads a single text observation."""
        sample = super().__getitem__(idx)
        idx = self.indices[idx]

        if self.cfg.dataset.add_eos_token_to_answer:
            # remove EOS from input ids
            # TODO: fix max length in this case to be + 1
            for key in ["input_ids", "attention_mask", "labels"]:
                if key in sample:
                    sample[key] = sample[key][:-1]

        chosen_input_ids, rejected_input_ids = self.get_answer_input_ids(idx)

        input_ids_not_padded = sample["input_ids"][
            torch.argwhere(sample["attention_mask"]).view(-1)
        ]
        max_length = max(
            [
                len(chosen_input_ids) + len(input_ids_not_padded),
                len(rejected_input_ids) + len(input_ids_not_padded),
                self.cfg.tokenizer.max_length,
            ]
        )

        for name, answer_input_ids in zip(
            ["chosen", "rejected"], [chosen_input_ids, rejected_input_ids]
        ):
            sample.update(
                {
                    f"{name}_{k}": v
                    for k, v in self.create_concatenated_inputs_and_labels(
                        input_ids_not_padded, answer_input_ids, max_length
                    ).items()
                }
            )
        return sample

    def create_concatenated_inputs_and_labels(
        self, prompt_input_ids, answer_input_ids, max_length
    ) -> dict:
        sample = {}
        input_ids = torch.cat([prompt_input_ids, answer_input_ids], dim=0)[-max_length:]
        # prompt inputs ids are not padded
        attention_mask = torch.ones(
            len(prompt_input_ids) + len(answer_input_ids),
            device=prompt_input_ids.device,
        )[-max_length:]
        # Need to right pad rejected and chosen answer to same length
        sample.update(
            self.right_pad_tokens(
                input_ids,
                attention_mask=attention_mask,
                max_length=max_length,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        )
        labels = sample["input_ids"].clone()
        labels[: len(prompt_input_ids)] = -100
        labels[labels == self.tokenizer.pad_token_id] = -100
        if self.cfg.dataset.add_eos_token_to_answer:
            # eos_token may be equal to pad_token. Add the label back manually.
            labels[
                torch.max(torch.where(sample["attention_mask"] != 0)[0]).cpu().item()
            ] = self.tokenizer.eos_token_id
        sample["labels"] = labels
        for key in [
            "input_ids",
            "attention_mask",
            "labels",
        ]:
            sample[key] = sample[key][-self.cfg.tokenizer.max_length :]

        return sample

    def get_answer_input_ids(self, idx):
        answer_input_ids = []
        for name, text in [
            ("chosen", self.chosen_answers[idx]),
            ("rejected", self.rejected_answer[idx]),
        ]:
            answer_input_id = self.encode(
                self.tokenizer,
                text=text,
                max_length=(
                    self.cfg.tokenizer.max_length_answer
                    - int(self.cfg.dataset.add_eos_token_to_answer)
                ),
                truncation_side="right",
            )["input_ids"]
            if self.cfg.dataset.add_eos_token_to_answer:
                answer_input_id = torch.cat(
                    [
                        answer_input_id,
                        torch.Tensor([self.tokenizer.eos_token_id]).long(),
                    ],
                    dim=0,
                )
            answer_input_ids.append(answer_input_id)
        return answer_input_ids

    def right_pad_tokens(
        self,
        input_ids,
        attention_mask,
        max_length,
        pad_token_id,
        prefix="",
    ):
        sample = {}
        sample[f"{prefix}input_ids"] = torch.full((max_length,), pad_token_id)
        sample[f"{prefix}input_ids"][: len(input_ids)] = input_ids
        sample[f"{prefix}attention_mask"] = torch.zeros(max_length)
        sample[f"{prefix}attention_mask"][: len(input_ids)] = attention_mask
        return sample

    def postprocess_batch_predictions(self, cfg: Any, batch, output: Dict) -> Dict:
        if cfg.prediction.metric == "Perplexity":
            return output

        predicted_text = [
            self.tokenizer.decode(ids, skip_special_tokens=True).strip()
            for ids in output["predicted_answer_ids"]
        ]
        output["predicted_text"] = np.array(predicted_text)
        input_text = [
            self.tokenizer.decode(ids, skip_special_tokens=True).strip()
            for ids in batch["prompt_input_ids"]
        ]
        output["input_text"] = np.array(input_text)

        if not cfg.training.use_rlhf:
            del output["predicted_answer_ids"]
        else:
            output["predicted_answer_ids"].detach()

        return output

    def postprocess_output(self, cfg, df: pd.DataFrame, output: Dict) -> Dict:
        output["target_text"] = self.chosen_answers
        metric_func, _, _ = cfg.prediction.metric_class.get(cfg.prediction.metric)
        if "GPT" in cfg.prediction.metric:
            metrics, explanations = metric_func(
                cfg,
                output,
                df,
                raw_results=True,
            )
            output["explanations"] = explanations
        else:
            metrics = metric_func(
                cfg,
                output,
                df,
            )
        output["metrics"] = metrics
        return output
