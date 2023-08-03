import os
from typing import Any, Dict

import pandas as pd

from llm_studio.src.datasets.text_causal_language_modeling_ds import CustomDataset
from llm_studio.src.datasets.text_utils import get_tokenizer
from llm_studio.src.utils.data_utils import (
    read_dataframe_drop_missing_labels,
    sample_indices,
)
from llm_studio.src.utils.plot_utils import (
    PlotData,
    format_for_markdown_visualization,
    list_to_markdown_representation,
)


class Plots:
    NUM_TEXTS: int = 20

    @classmethod
    def plot_batch(cls, batch, cfg) -> PlotData:
        tokenizer = get_tokenizer(cfg)

        df = pd.DataFrame(
            {
                "Prompt Text": [
                    tokenizer.decode(input_ids, skip_special_tokens=True)
                    for input_ids in batch["prompt_input_ids"].detach().cpu().numpy()
                ]
            }
        )
        df["Prompt Text"] = df["Prompt Text"].apply(format_for_markdown_visualization)
        if "labels" in batch.keys():
            df["Answer Text"] = [
                tokenizer.decode(
                    [label for label in labels if label != -100],
                    skip_special_tokens=True,
                )
                for labels in batch.get("labels", batch["input_ids"])
                .detach()
                .cpu()
                .numpy()
            ]
        tokens_list = [
            tokenizer.convert_ids_to_tokens(input_ids)
            for input_ids in batch["input_ids"].detach().cpu().numpy()
        ]
        masks_list = [
            [label != -100 for label in labels]
            for labels in batch.get("labels", batch["input_ids"]).detach().cpu().numpy()
        ]
        df["Tokenized Text"] = [
            list_to_markdown_representation(
                tokens, masks, pad_token=tokenizer.pad_token, num_chars=100
            )
            for tokens, masks in zip(tokens_list, masks_list)
        ]
        # limit to 2000 rows, still renders fast in wave
        df = df.iloc[:2000]

        # Convert into a scrollable table by transposing the dataframe
        df_transposed = pd.DataFrame(columns=["Sample Number", "Field", "Content"])
        for i, row in df.iterrows():
            offset = 3 if "Answer Text" in df.columns else 2
            df_transposed.loc[i * offset] = [
                i,
                "Prompt Text",
                row["Prompt Text"],
            ]
            if "Answer Text" in df.columns:
                df_transposed.loc[i * offset + 1] = [
                    i,
                    "Answer Text",
                    row["Answer Text"],
                ]
            df_transposed.loc[i * offset + 2] = [
                i,
                "Tokenized Text",
                row["Tokenized Text"],
            ]
        df_transposed["Content"] = df_transposed["Content"].apply(
            format_for_markdown_visualization
        )

        path = os.path.join(cfg.output_directory, "batch_viz.parquet")
        df_transposed.to_parquet(path)

        return PlotData(path, encoding="df")

    @classmethod
    def plot_data(cls, cfg) -> PlotData:
        df = read_dataframe_drop_missing_labels(cfg.dataset.train_dataframe, cfg)

        limit_chained_samples = cfg.dataset.limit_chained_samples
        cfg.dataset.limit_chained_samples = True
        dataset = CustomDataset(df, cfg, mode="validation")
        text_separator = "TEXT SEPARATOR"
        input_texts = [
            dataset.get_chained_prompt_text(i, text_separator=text_separator)
            for i in dataset.indices
        ]
        target_texts = [dataset.answers[i] for i in dataset.indices]
        cfg.dataset.limit_chained_samples = limit_chained_samples

        idxs = sample_indices(len(dataset.indices), Plots.NUM_TEXTS)
        input_texts = [input_texts[i] for i in idxs]
        target_texts = [target_texts[i] for i in idxs]

        df = pd.DataFrame(
            {
                "Input Text": input_texts,
                "Target Text": target_texts,
            }
        )
        # Convert into a scrollable table by transposing the dataframe
        df_transposed = pd.DataFrame(columns=["Sample Number", "Field", "Content"])

        i = 0
        for sample_number, row in df.iterrows():
            input_texts = row["Input Text"].split(text_separator)
            for j, input_text in enumerate(input_texts):
                suffix = "- Prompt" if j % 2 == 0 else "- Answer "
                df_transposed.loc[i] = [
                    sample_number,
                    f"Input Text {suffix}",
                    input_text,
                ]
                i += 1
            df_transposed.loc[i] = [sample_number, "Target Text", row["Target Text"]]
            i += 1

        df_transposed["Content"] = df_transposed["Content"].apply(
            format_for_markdown_visualization
        )
        path = os.path.join(
            os.path.dirname(cfg.dataset.train_dataframe), "data_viz.parquet"
        )
        df_transposed.to_parquet(path)

        return PlotData(path, encoding="df")

    @classmethod
    def plot_validation_predictions(
        cls, val_outputs: Dict, cfg: Any, val_df: pd.DataFrame, mode: str
    ) -> PlotData:
        assert mode in ["validation"]

        dataset = CustomDataset(val_df, cfg, mode="validation")
        input_texts = [dataset.get_chained_prompt_text(i) for i in range(len(dataset))]
        target_text = val_outputs["target_text"]
        if "predicted_text" in val_outputs.keys():
            predicted_text = val_outputs["predicted_text"]
        else:
            predicted_text = [
                "No predictions are generated for the selected metric"
            ] * len(target_text)

        df = pd.DataFrame(
            {
                "Input Text": input_texts,
                "Target Text": target_text,
                "Predicted Text": predicted_text,
            }
        )
        df["Input Text"] = df["Input Text"].apply(format_for_markdown_visualization)
        df["Target Text"] = df["Target Text"].apply(format_for_markdown_visualization)
        df["Predicted Text"] = df["Predicted Text"].apply(
            format_for_markdown_visualization
        )

        if val_outputs.get("metrics") is not None:
            df[f"Metric ({cfg.prediction.metric})"] = val_outputs["metrics"]
            df[f"Metric ({cfg.prediction.metric})"] = df[
                f"Metric ({cfg.prediction.metric})"
            ].round(decimals=3)
        if val_outputs.get("explanations") is not None:
            df["Explanation"] = val_outputs["explanations"]

        path = os.path.join(cfg.output_directory, f"{mode}_viz.parquet")
        df.to_parquet(path)
        return PlotData(data=path, encoding="df")

    @staticmethod
    def plot_empty(cfg, error="Not yet implemented.") -> PlotData:
        """Plots an empty default plot.

        Args:
            cfg: config

        Returns:
            The default plot as `PlotData`.
        """

        return PlotData(f"<h2>{error}</h2>", encoding="html")
