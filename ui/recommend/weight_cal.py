
from ui.models import (
    UserSmellingInput,UserSmellingMyScore,
    UserInfo, Perfume, PerfumeClassification,
    PerfumeColor, PerfumeSeason, Score,
    TopBottom, Dress, ClothesColor )
from django.db.models import Q
import numpy as np
import pandas as pd
import math, re
import joblib
import os
from sklearn.preprocessing import MinMaxScaler
from django.conf import settings
import warnings
warnings.filterwarnings("ignore")
import itertools

# =====================================================
def find_best_weights():
    k = 3

    # =====================================================
    # 0. 데이터 로드
    # =====================================================
    final_result = pd.DataFrame.from_records(
        UserSmellingMyScore.objects.all().values()
    )

    # Decimal → float 변환
    for col in ["style_score", "color_score", "season_score"]:
        if col in final_result.columns:
            final_result[col] = final_result[col].astype(float)

    user_smelling_df = pd.DataFrame.from_records(
        UserSmellingInput.objects
        .filter(smelling_user_id__range=(1001, 1100))
        .values()
    )

    # =====================================================
    # 1. 가중치 후보
    # =====================================================
    weight_candidates = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    weight_results = []

    # =====================================================
    # 2. 가중치 조합 탐색
    # =====================================================
    for w_style, w_color, w_season in itertools.product(weight_candidates, repeat=3):

        if w_style + w_color + w_season == 0:
            continue

        # 정규화
        total = w_style + w_color + w_season
        w_style /= total
        w_color /= total
        w_season /= total

        df = final_result.copy()
        df["myscore"] = (
            df["style_score"] * w_style +
            df["color_score"] * w_color +
            df["season_score"] * w_season
        )

        # =================================================
        # Precision@k
        # =================================================
        topk_df = (
            df.groupby("user_id", group_keys=False)
              .apply(lambda x: x.nlargest(k, "myscore"))
        )

        precisions = []

        perfume_col = "perfume_id" if "perfume_id" in user_smelling_df.columns else "perfume_id_id"
        user_col = "smelling_user_id"

        for uid in topk_df["user_id"].unique():
            recs = topk_df[topk_df["user_id"] == uid]["perfume_id"].tolist()

            actuals = user_smelling_df[
                user_smelling_df[user_col] == uid
            ][perfume_col].tolist()

            if not actuals:
                continue

            hit = len(set(recs) & set(actuals))
            precisions.append(hit / k)

        mean_prec = np.mean(precisions) if precisions else 0

        weight_results.append(
            (w_style, w_color, w_season, mean_prec)
        )

    # =====================================================
    # 3. 최적 가중치 선택
    # =====================================================
    best = max(weight_results, key=lambda x: x[3])

    best_w_style, best_w_color, best_w_season, best_precision = best

    print(
        f"🏆 Best weights → "
        f"style={best_w_style:.3f}, "
        f"color={best_w_color:.3f}, "
        f"season={best_w_season:.3f} "
        f"(precision@{k}={best_precision:.3f})"
    )

    return best_w_style, best_w_color, best_w_season
