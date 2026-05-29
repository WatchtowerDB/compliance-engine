-- MySQL dump 10.13  Distrib 9.7.0, for Linux (x86_64)
--
-- Host: localhost    Database: testdb
-- ------------------------------------------------------
-- Server version	9.7.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '359db840-50c2-11f1-a74f-ce3dd8604d1c:1-20';

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `event_timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `user_id` varchar(50) DEFAULT NULL,
  `event_type` varchar(50) DEFAULT NULL,
  `event_description` text,
  `data_accessed` varchar(100) DEFAULT NULL,
  `full_pan_viewed` tinyint(1) DEFAULT '0',
  `card_id` int DEFAULT NULL,
  `source_ip` varchar(45) DEFAULT NULL,
  `success` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`log_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
INSERT INTO `audit_logs` VALUES (1,'2026-01-15 10:30:00','user_sales','DATA_ACCESS','Viewed full cardholder data','cardholder_data',1,1,'192.168.1.10',1),(2,'2026-01-15 11:00:00','user_support','DATA_ACCESS','Accessed transaction details with full PAN','transactions',1,2,'192.168.1.11',1),(3,'2026-01-15 14:20:00','user_marketing','DATA_ACCESS','Exported customer payment data','cardholder_data',1,3,'192.168.1.12',1),(4,'2026-01-16 09:00:00','user_fraud','DATA_ACCESS','Fraud investigation - Case #12345','cardholder_data',1,1,'192.168.1.50',1),(5,'2026-01-16 10:00:00','user_cashier','DATA_ACCESS','Processed payment - masked PAN only','cardholder_data',0,4,'192.168.1.20',1);
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cardholder_data`
--

DROP TABLE IF EXISTS `cardholder_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cardholder_data` (
  `card_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `cardholder_name` varchar(100) DEFAULT NULL,
  `card_number` varchar(50) NOT NULL,
  `card_number_masked` varchar(50) DEFAULT NULL,
  `expiry_date` varchar(7) DEFAULT NULL,
  `cvv` varchar(4) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`card_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cardholder_data`
--

LOCK TABLES `cardholder_data` WRITE;
/*!40000 ALTER TABLE `cardholder_data` DISABLE KEYS */;
INSERT INTO `cardholder_data` VALUES (1,1001,'John Smith','4532015112830366','453201******0366','12/2026','123','2026-05-16 00:57:33'),(2,1002,'Jane Doe','5425233430109903','542523******9903','03/2027','456','2026-05-16 00:57:33'),(3,1003,'Bob Wilson','4916338506082832','491633******2832','09/2025','789','2026-05-16 00:57:33'),(4,2001,'Alice Johnson','************4589','************4589','06/2027',NULL,'2026-05-16 00:57:33'),(5,2002,'Charlie Brown','************7823','************7823','11/2026',NULL,'2026-05-16 00:57:33');
/*!40000 ALTER TABLE `cardholder_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transactions` (
  `transaction_id` int NOT NULL AUTO_INCREMENT,
  `card_id` int DEFAULT NULL,
  `merchant_id` int NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `full_pan` varchar(20) DEFAULT NULL,
  `sad_data` text,
  `authorization_code` varchar(20) DEFAULT NULL,
  `response_code` varchar(5) DEFAULT NULL,
  `transaction_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_by_user` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`transaction_id`),
  KEY `card_id` (`card_id`),
  CONSTRAINT `transactions_ibfk_1` FOREIGN KEY (`card_id`) REFERENCES `cardholder_data` (`card_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transactions`
--

LOCK TABLES `transactions` WRITE;
/*!40000 ALTER TABLE `transactions` DISABLE KEYS */;
INSERT INTO `transactions` VALUES (1,1,101,150.00,'4532015112830366','CVV=123;PIN_BLOCK=A1B2C3D4','AUTH001','00','2026-05-16 00:57:33','user_sales'),(2,2,101,275.50,'5425233430109903','CVV=456;TRACK2=5425233430109903D2703','AUTH002','00','2026-05-16 00:57:33','user_sales'),(3,3,102,89.99,'4916338506082832','CVV=789','AUTH003','00','2026-05-16 00:57:33','user_support'),(4,4,101,200.00,NULL,NULL,'AUTH004','00','2026-05-16 00:57:33','user_sales'),(5,5,102,350.00,NULL,NULL,'AUTH005','00','2026-05-16 00:57:33','user_sales');
/*!40000 ALTER TABLE `transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `department` varchar(50) DEFAULT NULL,
  `job_title` varchar(100) DEFAULT NULL,
  `can_view_full_pan` tinyint(1) DEFAULT '0',
  `requires_full_pan` tinyint(1) DEFAULT '0',
  `access_approved` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'user_sales','sales@company.com','Sales','Sales Representative',1,0,0,'2026-05-16 00:57:33'),(2,'user_support','support@company.com','Support','Customer Support',1,0,0,'2026-05-16 00:57:33'),(3,'user_marketing','marketing@company.com','Marketing','Marketing Analyst',1,0,0,'2026-05-16 00:57:33'),(4,'user_fraud','fraud@company.com','Fraud','Fraud Analyst',1,1,1,'2026-05-16 00:57:33'),(5,'user_cashier','cashier@company.com','Retail','Cashier',0,0,1,'2026-05-16 00:57:33');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-16  1:03:44
