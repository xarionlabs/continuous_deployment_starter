#!/usr/bin/env node

/**
 * Simplified database setup script for SQLite development
 */

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function setupDatabase() {
  console.log('🔧 Setting up SQLite database...');
  
  console.log('🔧 Generating Prisma client...');
  execSync('npx prisma generate', { stdio: 'inherit' });
  
  const migrationsPath = join(__dirname, '..', 'prisma', 'migrations');
  
  if (!existsSync(migrationsPath)) {
    console.log('🗄️  Creating initial migration...');
    execSync('npx prisma migrate dev --name init', { stdio: 'inherit' });
  } else {
    console.log('🗄️  Deploying migrations...');
    execSync('npx prisma migrate deploy', { stdio: 'inherit' });
  }
  
  console.log('✅ Database setup completed successfully!');
}

setupDatabase();