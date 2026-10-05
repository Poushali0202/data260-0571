CREATE DATABASE IF NOT EXISTS s0571_rel;
USE s0571_rel;
CREATE TABLE `suppliers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `region` varchar(200) NOT NULL,
  `email` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
;
CREATE TABLE `grocery_notices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_name` varchar(200) NOT NULL,
  `notice_code` varchar(20) NOT NULL,
  `notice_source` varchar(200) NOT NULL,
  `affected_units` int NOT NULL DEFAULT '0',
  `supplier_id` int NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `notice_code` (`notice_code`),
  KEY `supplier_id` (`supplier_id`),
  CONSTRAINT `grocery_notices_ibfk_1` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_affected_units` CHECK ((`affected_units` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5003 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
;
