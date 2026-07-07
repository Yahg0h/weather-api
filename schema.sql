-- =====================================================
-- Weather API - Database Schema
-- Version: 1.0.0
-- Created: 2026-07-07
-- Description: Complete schema for Weather API project
-- =====================================================
 
-- =====================================================
-- USERS TABLE
-- =====================================================
-- Stores user account information
-- Passwords are hashed using Argon2 before storage
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique user identifier',
    username VARCHAR(15) UNIQUE NOT NULL COMMENT 'Username for login (4-15 chars)',
    password VARCHAR(255) NOT NULL COMMENT 'Hashed password (Argon2)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Account creation timestamp',
    
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User accounts for Weather API';
 
 
-- =====================================================
-- CITIES TABLE
-- =====================================================
-- Stores cities saved by users for weather tracking
-- Includes latitude and longitude for API calls
-- =====================================================
CREATE TABLE IF NOT EXISTS cities (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique city identifier',
    user_id INT NOT NULL COMMENT 'Foreign key to users table',
    name VARCHAR(50) NOT NULL COMMENT 'City name (up to 50 chars)',
    latitude FLOAT NOT NULL COMMENT 'Geographic latitude (-90 to 90)',
    longitude FLOAT NOT NULL COMMENT 'Geographic longitude (-180 to 180)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When city was added to user list',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE COMMENT 'Cascade delete: removes cities when user is deleted',
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User-saved cities for weather tracking';
 
 
-- =====================================================
-- ON DELETE CASCADE BEHAVIOR
-- =====================================================
-- IMPORTANT: The cities table has ON DELETE CASCADE.
-- If a user is deleted from the users table, all cities
-- associated with that user will be automatically deleted.
-- 
-- Example:
-- DELETE FROM users WHERE id = 1;
-- → All cities with user_id = 1 are automatically deleted
-- =====================================================
 
-- =====================================================
-- SCHEMA VERSIONING
-- =====================================================
-- v1.0.0 (2026-07-07): Initial schema creation
--   - Created users table with Argon2 password storage
--   - Created cities table with geolocation coordinates
--   - Added indexes on user_id and created_at for performance
--   - Implemented ON DELETE CASCADE for data integrity
-- =====================================================