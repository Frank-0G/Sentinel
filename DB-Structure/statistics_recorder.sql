-- phpMyAdmin SQL Dump
-- Domain: OpenTTD Sentinel Statistics
-- Table: openttd_company_stats
-- ############################################################################
-- # OpenTTD Sentinel - Statistics Recorder Plugin
-- ############################################################################
-- # This table is used by the 'statistics_recorder.py' plugin to store 
-- # detailed historical metrics collected from the Gamescript.
-- # 
-- # Columns are sorted by importance: Meta -> Performance -> Finance -> Fleet -> Infra
-- ############################################################################

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS `openttd_company_stats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    -- Meta Info
    `server_id` INT NOT NULL,
    `timestamp` BIGINT NOT NULL,
    `datetime` DATETIME NOT NULL,
    `company_id` INT NOT NULL,
    
    -- High Level Performance
    `performance_rating` INT DEFAULT 0,
    `income` BIGINT DEFAULT 0,
    `bank_balance` BIGINT DEFAULT 0,
    `loan` BIGINT DEFAULT 0,
    `cargo_delivered` INT DEFAULT 0,
    
    -- Fleet Overview
    `v_count` INT DEFAULT 0,
    `avg_veh_age` INT DEFAULT 0,
    `stopped_vehs` INT DEFAULT 0,
    `stopped_val` BIGINT DEFAULT 0,
    `crashed_vehs` INT DEFAULT 0,
    `crashed_val` BIGINT DEFAULT 0,
    `loss_vehs` INT DEFAULT 0,
    `loss_val` BIGINT DEFAULT 0,
    `old_vehs` INT DEFAULT 0,
    `old_val` BIGINT DEFAULT 0,
    
    -- Network Quality
    `avg_station_rating` INT DEFAULT 0,
    `avg_town_rating` INT DEFAULT 0,
    `cargo_types_transported` INT DEFAULT 0,
    `station_count` INT DEFAULT 0,
    `serviced_station_count` INT DEFAULT 0,
    
    -- Infrastructure Counts (Granular)
    `infra_rail` INT DEFAULT 0,
    `infra_road` INT DEFAULT 0,
    `infra_tram` INT DEFAULT 0,
    `infra_signals` INT DEFAULT 0,
    `infra_canals` INT DEFAULT 0,
    `infra_station` INT DEFAULT 0,
    `infra_airport` INT DEFAULT 0,
    `infra_dock` INT DEFAULT 0,
    
    INDEX `idx_server_co_time` (`server_id`, `company_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
