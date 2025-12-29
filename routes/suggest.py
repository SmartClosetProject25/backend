from flask import Blueprint, request, jsonify
import json
import os
from dotenv import load_dotenv

import services.ai.ai_outfit_suggestion as aiOutfitSuggestion
from models.coordinate_model import CoordinateModel

# 環境変数をロード
load_dotenv()

def load_test_data():
    """テストデータをJSONファイルから読み込む"""
    test_data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_outfit_proposals.json')
    with open(test_data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

suggest_bp = Blueprint('suggest', __name__)

@suggest_bp.route('/send_today_plan', methods=['POST'])
def send_today_plan():
    try:
        # 今日の予定データを取得
        data = request.get_json()
        print("================================")
        print("【受信】今日の予定データ:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("================================")

        # user_idを固定値1に設定
        user_id = 1
        
        # 環境変数からテストモードを取得（デフォルトはFalse = 本番モード）
        use_test_data = os.getenv('USE_TEST_DATA', 'false').lower() in ('true', '1', 'yes')
        
        if use_test_data:
            # テストデータをJSONファイルから読み込む
            result = load_test_data()
            print("テストデータを使用しました")
        else:
            # 今日の予定データを生成(データベースからアイテムを取得)
            result = aiOutfitSuggestion.generate_outfit_suggestion(data, user_id=user_id)
            print("実際のAPIを呼び出しました")
        
        # print("生成されたコーディネート:")
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 提案されたコーディネートをデータベースに保存
        saved_coordinate_ids = []
        try:
            if 'proposals' in result and isinstance(result['proposals'], list):
                for proposal in result['proposals']:
                    if 'items' in proposal and 'tops' in proposal['items'] and 'bottoms' in proposal['items']:
                        top_id = proposal['items']['tops']['id']
                        bottom_id = proposal['items']['bottoms']['id']
                        outer_id = proposal['items'].get('outer', {}).get('id') if 'outer' in proposal['items'] else None
                        
                        # アイテムの詳細情報（seasons, color_name）をデータベースから取得
                        item_ids = [top_id, bottom_id]
                        if outer_id:
                            item_ids.append(outer_id)
                        items_info = CoordinateModel.get_item_info(item_ids)
                        
                        # sceneを決定（tasteから推測）
                        tops_taste = proposal['items']['tops'].get('taste', [])
                        bottoms_taste = proposal['items']['bottoms'].get('taste', [])
                        # outerのtasteも考慮
                        outer_taste = proposal['items'].get('outer', {}).get('taste', []) if 'outer' in proposal['items'] else []
                        all_taste = list(set(tops_taste + bottoms_taste + outer_taste))
                        
                        # tasteからsceneを推測（優先順位: ストリート > カジュアル > きれいめ > フォーマル）
                        scene = 'カジュアル'  # デフォルト
                        if 'ストリート' in all_taste:
                            scene = 'ストリート'
                        elif 'カジュアル' in all_taste:
                            scene = 'カジュアル'
                        elif 'きれいめ' in all_taste or 'フォーマル' in all_taste:
                            scene = 'きれいめ'
                        
                        # styleはsceneと同じ値を使用
                        style = scene
                        
                        # seasonを取得（トップス、ボトムス、アウターのseasonsを統合）
                        top_seasons = items_info.get(top_id, {}).get('seasons', '')
                        bottom_seasons = items_info.get(bottom_id, {}).get('seasons', '')
                        outer_seasons = items_info.get(outer_id, {}).get('seasons', '') if outer_id else ''
                        
                        # シーズンを統合（重複を除去）
                        all_seasons = []
                        if top_seasons:
                            all_seasons.extend([s.strip() for s in top_seasons.split(',')])
                        if bottom_seasons:
                            all_seasons.extend([s.strip() for s in bottom_seasons.split(',')])
                        if outer_seasons:
                            all_seasons.extend([s.strip() for s in outer_seasons.split(',')])
                        
                        # 重複を除去してソート
                        unique_seasons = sorted(list(set([s for s in all_seasons if s])))
                        season_str = ','.join(unique_seasons) if unique_seasons else ''
                        
                        # color_schemeを生成（トップス×ボトムス）
                        top_color = items_info.get(top_id, {}).get('color_name', '')
                        bottom_color = items_info.get(bottom_id, {}).get('color_name', '')
                        color_scheme = f"{top_color}×{bottom_color}" if top_color and bottom_color else ''
                        
                        # features_jsonを作成（既存のデータ形式に合わせる）
                        features_data = {
                            "style": style,
                            "season": season_str,
                            "color_scheme": color_scheme
                        }
                        
                        features_json = json.dumps(features_data, ensure_ascii=False)
                        
                        # coordinatesテーブルに挿入
                        coordinate_id = CoordinateModel.create_coordinate(
                            user_id=user_id,
                            top_id=top_id,
                            bottom_id=bottom_id,
                            outer_id=outer_id,
                            scene=scene,
                            features_json=features_json
                        )
                        
                        if coordinate_id:
                            saved_coordinate_ids.append(coordinate_id)
                            # 提案データにcoordinate_idを追加
                            proposal['coordinate_id'] = coordinate_id
                            print(f"  features_json: {features_json}")
            
            print(f"合計{len(saved_coordinate_ids)}件のコーディネートをデータベースに保存しました")
            
        except Exception as db_error:
            print(f"データベース保存エラー: {str(db_error)}")
            import traceback
            traceback.print_exc()
            # データベースエラーが発生しても、提案結果は返す
        
        # フロントエンドに結果を返す
        return jsonify(result), 200

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

