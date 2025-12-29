from flask import Blueprint, request, jsonify
import json
import os
from dotenv import load_dotenv

import services.ai.ai_outfit_suggestion as aiOutfitSuggestion
from utils.db_con import get_db_connection

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
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 各提案をcoordinatesテーブルに保存
            saved_coordinate_ids = []
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
                        placeholders = ','.join(['%s'] * len(item_ids))
                        item_sql = f"""
                            SELECT 
                                i.item_id,
                                i.seasons,
                                col.color_name
                            FROM items i
                            INNER JOIN colors col ON i.color_id = col.color_id
                            WHERE i.item_id IN ({placeholders}) AND i.is_deleted = 0
                        """
                        cursor.execute(item_sql, tuple(item_ids))
                        item_rows = cursor.fetchall()
                        
                        # アイテム情報を辞書に変換
                        items_info = {row['item_id']: row for row in item_rows}
                        
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
                        insert_sql = """
                            INSERT INTO coordinates (user_id, top_id, bottom_id, outer_id, scene, features_json, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """
                        cursor.execute(insert_sql, (user_id, top_id, bottom_id, outer_id, scene, features_json))
                        coordinate_id = cursor.lastrowid
                        saved_coordinate_ids.append(coordinate_id)
                        
                        # 提案データにcoordinate_idを追加
                        proposal['coordinate_id'] = coordinate_id
                        
                        print(f"  features_json: {features_json}")
            
            conn.commit()
            print(f"合計{len(saved_coordinate_ids)}件のコーディネートをデータベースに保存しました")
            
        except Exception as db_error:
            print(f"データベース保存エラー: {str(db_error)}")
            import traceback
            traceback.print_exc()
            # データベースエラーが発生しても、提案結果は返す
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        # フロントエンドに結果を返す
        return jsonify(result), 200

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

