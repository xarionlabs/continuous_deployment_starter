#!/usr/bin/env node

/**
 * Simple script to validate database configuration
 * This script checks that the DATABASE_PROVIDER and DATABASE_URL environment variables are set correctly
 */

import { execSync } from 'child_process';

function validateConfig() {
  console.log('🔍 Validating database configuration...');
  
  const provider = process.env.DATABASE_PROVIDER;
  const url = process.env.DATABASE_URL;
  
  if (!provider) {
    console.error('❌ DATABASE_PROVIDER environment variable is not set');
    process.exit(1);
  }
  
  if (!url) {
    console.error('❌ DATABASE_URL environment variable is not set');
    process.exit(1);
  }
  
  console.log(`📊 Database Provider: ${provider}`);
  console.log(`🔗 Database URL: ${url.replace(/:[^:@]*@/, ':***@')}`); // Hide password
  
  // Validate provider
  if (!['sqlite', 'postgresql'].includes(provider)) {
    console.error('❌ DATABASE_PROVIDER must be either "sqlite" or "postgresql"');
    process.exit(1);
  }
  
  // Validate URL format
  if (provider === 'sqlite' && !url.startsWith('file:')) {
    console.error('❌ SQLite DATABASE_URL must start with "file:"');
    process.exit(1);
  }
  
  if (provider === 'postgresql' && !url.startsWith('postgresql://')) {
    console.error('❌ PostgreSQL DATABASE_URL must start with "postgresql://"');
    process.exit(1);
  }
  
  console.log('✅ Database configuration is valid');
  
  // Test Prisma schema generation
  try {
    console.log('🔧 Testing Prisma client generation...');
    execSync('npx prisma generate', { stdio: 'inherit' });
    console.log('✅ Prisma client generated successfully');
  } catch (error) {
    console.error('❌ Failed to generate Prisma client:', error.message);
    process.exit(1);
  }
}

validateConfig();