#!/usr/bin/env node

/**
 * Database setup script that switches between SQLite and PostgreSQL schemas
 * based on the DATABASE_PROVIDER environment variable
 */

import { copyFileSync, existsSync, rmSync } from 'fs';
import { execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function setupDatabase() {
  const provider = process.env.DATABASE_PROVIDER || 'sqlite';
  
  console.log(`🔧 Setting up database for ${provider}...`);
  
  const schemaPath = join(__dirname, '..', 'prisma', 'schema.prisma');
  const sqliteSchemaPath = join(__dirname, '..', 'prisma', 'schema.sqlite.prisma');
  
  if (provider === 'sqlite') {
    if (!existsSync(sqliteSchemaPath)) {
      console.error('❌ SQLite schema file not found at:', sqliteSchemaPath);
      process.exit(1);
    }
    
    console.log('📋 Copying SQLite schema...');
    copyFileSync(sqliteSchemaPath, schemaPath);
    
    console.log('🔧 Generating Prisma client...');
    execSync('npx prisma generate', { stdio: 'inherit' });
    
    console.log('🗄️  Running database migrations...');
    // For SQLite, we need to remove the migrations directory since we're switching from PostgreSQL
    const migrationsPath = join(__dirname, '..', 'prisma', 'migrations');
    if (existsSync(migrationsPath)) {
      console.log('🧹 Removing PostgreSQL migrations directory...');
      rmSync(migrationsPath, { recursive: true, force: true });
    }
    execSync('npx prisma migrate dev --name init', { stdio: 'inherit' });
    
  } else if (provider === 'postgresql') {
    // PostgreSQL schema is already the default
    console.log('📋 Using PostgreSQL schema (default)...');
    
    // Ensure we have the PostgreSQL schema
    const postgresqlSchemaPath = join(__dirname, '..', 'prisma', 'schema.postgresql.prisma');
    if (!existsSync(postgresqlSchemaPath)) {
      // Create PostgreSQL schema from current schema if it doesn't exist
      copyFileSync(schemaPath, postgresqlSchemaPath);
    }
    
    console.log('🔧 Generating Prisma client...');
    execSync('npx prisma generate', { stdio: 'inherit' });
    
    console.log('🗄️  Running database migrations...');
    execSync('npx prisma migrate deploy', { stdio: 'inherit' });
    
  } else {
    console.error('❌ Unknown DATABASE_PROVIDER:', provider);
    console.error('   Supported providers: sqlite, postgresql');
    process.exit(1);
  }
  
  console.log('✅ Database setup completed successfully!');
}

setupDatabase();