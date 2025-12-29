-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- ホスト: 127.0.0.1
-- 生成日時: 2025-12-28 11:11:22
-- サーバのバージョン： 8.0.31
-- PHP のバージョン: 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- データベース: `2025gp2`
--

-- --------------------------------------------------------

--
-- テーブルの構造 `ab_logs`
--

CREATE TABLE `ab_logs` (
  `log_id` int NOT NULL,
  `user_id` int NOT NULL,
  `scene` varchar(50) NOT NULL,
  `temp_c` int NOT NULL,
  `coordinate_a` int NOT NULL,
  `coordinate_b` int NOT NULL,
  `chosen` varchar(10) NOT NULL,
  `decision_ms` varchar(500) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- テーブルの構造 `categories`
--

CREATE TABLE `categories` (
  `category_id` int NOT NULL,
  `category` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `categories`
--

INSERT INTO `categories` (`category_id`, `category`) VALUES
(1, 'トップス'),
(2, 'ジャケット・アウター'),
(3, 'パンツ'),
(4, 'スカート');

-- --------------------------------------------------------

--
-- テーブルの構造 `category_details`
--

CREATE TABLE `category_details` (
  `category_detail_id` int NOT NULL,
  `category_detail` varchar(50) NOT NULL,
  `category_id` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `category_details`
--

INSERT INTO `category_details` (`category_detail_id`, `category_detail`, `category_id`) VALUES
(1, 'Tシャツ・カットソー', 1),
(2, 'シャツ・ブラウス', 1),
(3, 'ビジネスシャツ', 1),
(4, 'ポロシャツ', 1),
(5, 'ニット・セーター', 1),
(6, 'ベスト', 1),
(7, 'パーカー', 1),
(8, 'スウェット', 1),
(9, 'カーディガン・ボレロ', 1),
(10, 'アンサンブル', 1),
(11, 'ジャージ', 1),
(12, 'タンクトップ', 1),
(13, 'キャミソール', 1),
(14, 'チューブトップ', 1),
(15, 'その他トップス', 1),
(16, 'テーラードジャケット', 2),
(17, 'ノーカラージャケット', 2),
(18, 'ノーカラーコート', 2),
(19, 'デニムジャケット', 2),
(20, 'ライダースジャケット', 2),
(21, 'ブルゾン', 2),
(22, 'ミリタリージャケット', 2),
(23, 'MA-1', 2),
(24, 'ダウンジャケット・コート', 2),
(25, 'モッズコート', 2),
(26, 'ピーコート', 2),
(27, 'スンカラーコート', 2),
(28, 'トレンチコート', 2),
(29, 'チェスターコート', 2),
(30, 'ムートンコート', 2),
(31, 'ナイロンジャケット', 2),
(32, 'マウンテンパーカー', 2),
(33, 'スタジャン', 2),
(34, 'スカジャン', 2),
(35, 'セットアップ', 2),
(36, 'カバーオール', 2),
(37, 'ポンチョ', 2),
(38, 'その他アウター', 2),
(39, 'デニムパンツ', 3),
(40, 'カーゴパンツ', 3),
(41, 'チノパンツ', 3),
(42, 'スウェットパンツ', 3),
(43, 'スラックス', 3),
(44, 'その他パンツ', 3),
(45, 'デニムスカート', 4),
(46, 'その他スカート', 4);

-- --------------------------------------------------------

--
-- テーブルの構造 `colors`
--

CREATE TABLE `colors` (
  `color_id` int NOT NULL,
  `color_name` varchar(50) NOT NULL,
  `color_code` char(7) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `colors`
--

INSERT INTO `colors` (`color_id`, `color_name`, `color_code`) VALUES
(1, 'ホワイト', '#FFFFFF'),
(2, 'オフホワイト', '#FAF9F6'),
(3, 'アイボリー', '#FFF8E7'),
(4, 'ベージュ', '#F5F5DC'),
(5, 'ライトベージュ', '#F0E5CF'),
(6, 'モカ', '#C8A27A'),
(7, 'イエロー', '#FFF9B1'),
(8, 'オレンジ', '#FFD6A5'),
(9, 'ピンク', '#FFD1DC'),
(10, 'ライトピンク', '#FFE4E1'),
(11, 'ラベンダー', '#E6E6FA'),
(12, 'スカイブルー', '#CBE8FA'),
(13, 'ライトブルー', '#ADD8E6'),
(14, 'ミントグリーン', '#CFFFE5'),
(15, 'ライトグリーン', '#CCF5CC'),
(16, 'カーキ', '#E6E2B3'),
(17, 'グレー', '#D3D3D3'),
(18, 'チャコールグレー', '#BEBEBE'),
(19, 'ブラック', '#555555');

-- --------------------------------------------------------

--
-- テーブルの構造 `coordinates`
--

CREATE TABLE `coordinates` (
  `coordinate_id` int NOT NULL,
  `user_id` int NOT NULL,
  `top_id` int NOT NULL,
  `bottom_id` int NOT NULL,
  `scene` varchar(50) DEFAULT NULL,
  `features_json` text,
  `outer_id` int DEFAULT NULL,
  `genimg_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `rating` enum('good','bad') DEFAULT NULL COMMENT 'tいいねfバット',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- テーブルの構造 `items`
--

CREATE TABLE `items` (
  `item_id` int NOT NULL,
  `color_id` int NOT NULL,
  `pattern_id` int NOT NULL,
  `size_id` int NOT NULL,
  `material` varchar(500) NOT NULL,
  `brand` varchar(300) NOT NULL,
  `taste` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `seasons` varchar(100) NOT NULL,
  `features` varchar(500) NOT NULL,
  `category_detail_id` int NOT NULL,
  `user_id` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `item_name` varchar(255) NOT NULL,
  `image_path` varchar(500) NOT NULL,
  `is_favorite` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `items`
--

INSERT INTO `items` (`item_id`, `color_id`, `pattern_id`, `size_id`, `material`, `brand`, `taste`, `seasons`, `features`, `category_detail_id`, `user_id`, `created_at`, `updated_at`, `is_deleted`, `item_name`, `image_path`, `is_favorite`) VALUES
(3, 1, 1, 3, '2', 'UNIQLO', '2', '1', '0', 1, 1, '2025-12-02 18:05:17', '2025-12-02 18:05:17', 0, 'テストTシャツ', '/static/images/1/clothes/clothes_3d8c85b8eb2b4d5c90175dd424a0a1d0.jpg', 0),
(4, 1, 1, 3, '綿', 'UNIQLO', 'カジュアル,きれいめ', '夏,春', '半袖,クルーネック', 1, 1, NOW(), NOW(), 0, '白Tシャツ', '/static/images/1/clothes/t001.jpg', 0),
(5, 19, 1, 3, '綿', 'UNIQLO', 'カジュアル,きれいめ', '夏,春', '半袖,Vネック', 1, 1, NOW(), NOW(), 0, '黒Tシャツ', '/static/images/1/clothes/t002.jpg', 0),
(6, 1, 1, 3, '綿', 'UNIQLO', 'きれいめ,カジュアル,フォーマル', '春,秋', '長袖,ボタンダウン,カジュアル', 2, 1, NOW(), NOW(), 0, '白シャツ', '/static/images/1/clothes/t003.jpg', 0),
(7, 19, 1, 3, 'ウール', 'UNIQLO', 'きれいめ,カジュアル', '冬', '長袖,クルーネック,厚手', 5, 1, NOW(), NOW(), 0, 'ネイビーニット', '/static/images/1/clothes/t004.jpg', 0),
(8, 17, 1, 3, 'カシミヤ', 'UNIQLO', 'きれいめ,カジュアル', '冬,秋', '長袖,Vネック,薄手', 5, 1, NOW(), NOW(), 0, 'グレーニット', '/static/images/1/clothes/t005.jpg', 0),
(9, 17, 1, 3, '綿', 'UNIQLO', 'カジュアル,ストリート', '春,秋', '長袖,フード付き,裏起毛なし', 7, 1, NOW(), NOW(), 0, 'グレーパーカー', '/static/images/1/clothes/t006.jpg', 0),
(10, 13, 1, 3, '綿', 'UNIQLO', 'きれいめ,カジュアル', '春,夏,秋,冬', '長袖,ボタンダウン', 2, 1, NOW(), NOW(), 0, 'サックスブルーシャツ', '/static/images/1/clothes/t007.jpg', 0),
(11, 19, 1, 3, '綿', 'UNIQLO', 'カジュアル,きれいめ', '春,夏,秋', '半袖,ボタンダウン', 4, 1, NOW(), NOW(), 0, 'ネイビーポロシャツ', '/static/images/1/clothes/t008.jpg', 0),
(12, 19, 1, 3, 'デニム', 'UNIQLO', 'カジュアル', '春,夏,秋,冬', 'ロング丈,ストレート', 39, 1, NOW(), NOW(), 0, 'インディゴデニムパンツ', '/static/images/1/clothes/b001.jpg', 0),
(13, 19, 1, 3, 'ポリエステル', 'UNIQLO', 'きれいめ,フォーマル', '春,夏,秋,冬', 'ロング丈,テーパード,センタープレス', 43, 1, NOW(), NOW(), 0, '黒スラックス', '/static/images/1/clothes/b002.jpg', 0),
(14, 17, 1, 3, 'ウール', 'UNIQLO', 'きれいめ,フォーマル', '冬,秋', 'ロング丈,ストレート', 43, 1, NOW(), NOW(), 0, 'グレースラックス', '/static/images/1/clothes/b003.jpg', 0),
(15, 4, 1, 3, '綿', 'UNIQLO', 'カジュアル', '春,秋,冬', 'ロング丈,ストレート', 41, 1, NOW(), NOW(), 0, 'ベージュチノパンツ', '/static/images/1/clothes/b004.jpg', 0),
(16, 19, 1, 3, 'デニム', 'UNIQLO', 'カジュアル,きれいめ', '春,秋,冬', 'ロング丈,スリム', 39, 1, NOW(), NOW(), 0, '黒デニムパンツ', '/static/images/1/clothes/b005.jpg', 0),
(17, 16, 1, 3, '綿', 'UNIQLO', 'カジュアル,ストリート', '春,夏,秋', 'ロング丈,ストレート,ポケット付き', 40, 1, NOW(), NOW(), 0, 'カーキカーゴパンツ', '/static/images/1/clothes/b006.jpg', 0),
(18, 19, 1, 3, 'ポリエステル', 'UNIQLO', 'きれいめ,フォーマル', '春,秋', '長袖,シングル', 16, 1, NOW(), NOW(), 0, 'ネイビーテーラードジャケット', '/static/images/1/clothes/o001.jpg', 0),
(19, 19, 1, 3, 'ダウン', 'UNIQLO', 'カジュアル,きれいめ', '冬', '長袖,フード付き,ロング丈', 24, 1, NOW(), NOW(), 0, '黒ダウンコート', '/static/images/1/clothes/o002.jpg', 0),
(20, 4, 1, 3, '綿', 'UNIQLO', 'きれいめ,トラッド', '春,秋', '長袖,ロング丈,ベルト付き', 28, 1, NOW(), NOW(), 0, 'ベージュトレンチコート', '/static/images/1/clothes/o003.jpg', 0),
(21, 16, 1, 3, 'ナイロン', 'UNIQLO', 'カジュアル,ミリタリー', '春,秋', 'ショート丈,中綿なし,リブ', 21, 1, NOW(), NOW(), 0, 'カーキMA-1', '/static/images/1/clothes/o004.jpg', 0),
(22, 18, 1, 3, 'ウール', 'UNIQLO', 'きれいめ,フォーマル', '冬', 'ロング丈,シングル,厚手', 28, 1, NOW(), NOW(), 0, 'グレーチェスターコート', '/static/images/1/clothes/o005.jpg', 0),
(23, 2, 1, 3, 'ポリエステル', 'UNIQLO', 'カジュアル,リラックス', '春,秋,冬', '長袖,スタンドカラー,ボア', 25, 1, NOW(), NOW(), 0, 'オフホワイトフリース', '/static/images/1/clothes/o006.jpg', 0);

-- --------------------------------------------------------

--
-- テーブルの構造 `patterns`
--

CREATE TABLE `patterns` (
  `pattern_id` int NOT NULL,
  `pattern_name` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `patterns`
--

INSERT INTO `patterns` (`pattern_id`, `pattern_name`) VALUES
(1, '無地'),
(2, 'ボーダー柄'),
(3, 'ドット柄'),
(4, 'ストライプ柄'),
(5, 'チェック柄'),
(6, '花柄・ボタニカル柄'),
(7, 'カモフラージュ柄'),
(8, 'ペイズリー柄'),
(9, 'レオパード柄'),
(10, 'パイソン柄'),
(11, 'ゼブラ柄'),
(12, '前面プリント'),
(13, 'バックプリント'),
(14, 'ワンポイント'),
(15, 'ブランドロゴ'),
(16, 'レース'),
(17, 'フリル'),
(18, 'フリンジ'),
(19, 'ビジュー'),
(20, '刺繍'),
(21, 'リボン'),
(22, 'キルティング'),
(23, 'ライン柄'),
(24, 'その他総柄');

-- --------------------------------------------------------

--
-- テーブルの構造 `profile`
--

CREATE TABLE `profile` (
  `profile_id` int NOT NULL,
  `user_id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `gender` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `height` int DEFAULT NULL,
  `weight` int DEFAULT NULL,
  `personal_color` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `skeleton` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- テーブルの構造 `size`
--

CREATE TABLE `size` (
  `size_id` int NOT NULL,
  `size` varchar(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `size`
--

INSERT INTO `size` (`size_id`, `size`) VALUES
(1, 'XS'),
(2, 'S'),
(3, 'M'),
(4, 'L'),
(5, 'XL'),
(6, 'XXL'),
(7, '3XL'),
(8, '4XL');

-- --------------------------------------------------------

--
-- テーブルの構造 `users`
--

CREATE TABLE `users` (
  `user_id` int NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `gender` int DEFAULT NULL,
  `trend` json DEFAULT NULL COMMENT 'お気に入り傾向',
  `height` int DEFAULT NULL,
  `weight` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- テーブルのデータのダンプ `users`
--

INSERT INTO `users` (`user_id`, `email`, `password`, `created_at`, `updated_at`, `is_deleted`, `username`, `gender`, `trend`, `height`, `weight`) VALUES
(1, 'test@example.com', 'hashed_password', NOW(), NOW(), 0, 'テストユーザー', NULL, NULL, NULL, NULL);

--
-- ダンプしたテーブルのインデックス
--

--
-- テーブルのインデックス `ab_logs`
--
ALTER TABLE `ab_logs`
  ADD PRIMARY KEY (`log_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `coordinate_a` (`coordinate_a`),
  ADD KEY `coordinate_b` (`coordinate_b`);

--
-- テーブルのインデックス `categories`
--
ALTER TABLE `categories`
  ADD PRIMARY KEY (`category_id`);

--
-- テーブルのインデックス `category_details`
--
ALTER TABLE `category_details`
  ADD PRIMARY KEY (`category_detail_id`),
  ADD KEY `category_details_ibfk_1` (`category_id`);

--
-- テーブルのインデックス `colors`
--
ALTER TABLE `colors`
  ADD PRIMARY KEY (`color_id`);

--
-- テーブルのインデックス `coordinates`
--
ALTER TABLE `coordinates`
  ADD PRIMARY KEY (`coordinate_id`),
  ADD KEY `top_id` (`top_id`),
  ADD KEY `bottom_id` (`bottom_id`),
  ADD KEY `coordinates_ibfk_4` (`oher_id`),
  ADD KEY `coordinates_ibfk_3` (`user_id`);

--
-- テーブルのインデックス `items`
--
ALTER TABLE `items`
  ADD PRIMARY KEY (`item_id`),
  ADD KEY `color_id` (`color_id`),
  ADD KEY `pattern_id` (`pattern_id`),
  ADD KEY `category_detail_id` (`category_detail_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `size_id` (`size_id`);

--
-- テーブルのインデックス `patterns`
--
ALTER TABLE `patterns`
  ADD PRIMARY KEY (`pattern_id`);

--
-- テーブルのインデックス `profile`
--
ALTER TABLE `profile`
  ADD PRIMARY KEY (`profile_id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- テーブルのインデックス `size`
--
ALTER TABLE `size`
  ADD PRIMARY KEY (`size_id`);

--
-- テーブルのインデックス `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`);

--
-- ダンプしたテーブルの AUTO_INCREMENT
--

--
-- テーブルの AUTO_INCREMENT `ab_logs`
--
ALTER TABLE `ab_logs`
  MODIFY `log_id` int NOT NULL AUTO_INCREMENT;

--
-- テーブルの AUTO_INCREMENT `categories`
--
ALTER TABLE `categories`
  MODIFY `category_id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- テーブルの AUTO_INCREMENT `category_details`
--
ALTER TABLE `category_details`
  MODIFY `category_detail_id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=47;

--
-- テーブルの AUTO_INCREMENT `colors`
--
ALTER TABLE `colors`
  MODIFY `color_id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- テーブルの AUTO_INCREMENT `coordinates`
--
ALTER TABLE `coordinates`
  MODIFY `coordinate_id` int NOT NULL AUTO_INCREMENT,
  ADD PRIMARY KEY (`coordinate_id`);

--
-- テーブルの AUTO_INCREMENT `items`
--
ALTER TABLE `items`
  MODIFY `item_id` int NOT NULL AUTO_INCREMENT;

--
-- テーブルの AUTO_INCREMENT `patterns`
--
ALTER TABLE `patterns`
  MODIFY `pattern_id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- テーブルの AUTO_INCREMENT `profile`
--
ALTER TABLE `profile`
  MODIFY `profile_id` int NOT NULL AUTO_INCREMENT;

--
-- テーブルの AUTO_INCREMENT `size`
--
ALTER TABLE `size`
  MODIFY `size_id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- テーブルの AUTO_INCREMENT `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int NOT NULL AUTO_INCREMENT;

--
-- ダンプしたテーブルの制約
--

--
-- テーブルの制約 `ab_logs`
--
ALTER TABLE `ab_logs`
  ADD CONSTRAINT `ab_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `ab_logs_ibfk_2` FOREIGN KEY (`coordinate_a`) REFERENCES `coordinates` (`coordinate_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `ab_logs_ibfk_3` FOREIGN KEY (`coordinate_b`) REFERENCES `coordinates` (`coordinate_id`) ON DELETE RESTRICT ON UPDATE RESTRICT;

--
-- テーブルの制約 `category_details`
--
ALTER TABLE `category_details`
  ADD CONSTRAINT `category_details_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT ON UPDATE RESTRICT;

--
-- テーブルの制約 `coordinates`
--
ALTER TABLE `coordinates`
  ADD CONSTRAINT `coordinates_ibfk_1` FOREIGN KEY (`top_id`) REFERENCES `items` (`item_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `coordinates_ibfk_2` FOREIGN KEY (`bottom_id`) REFERENCES `items` (`item_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `coordinates_ibfk_3` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `coordinates_ibfk_4` FOREIGN KEY (`oher_id`) REFERENCES `items` (`item_id`) ON DELETE RESTRICT ON UPDATE RESTRICT;

--
-- テーブルの制約 `items`
--
ALTER TABLE `items`
  ADD CONSTRAINT `items_ibfk_1` FOREIGN KEY (`color_id`) REFERENCES `colors` (`color_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `items_ibfk_2` FOREIGN KEY (`pattern_id`) REFERENCES `patterns` (`pattern_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `items_ibfk_3` FOREIGN KEY (`category_detail_id`) REFERENCES `category_details` (`category_detail_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `items_ibfk_4` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  ADD CONSTRAINT `items_ibfk_5` FOREIGN KEY (`size_id`) REFERENCES `size` (`size_id`) ON DELETE RESTRICT ON UPDATE RESTRICT;

--
-- テーブルの制約 `profile`
--
ALTER TABLE `profile`
  ADD CONSTRAINT `fk_profile_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
