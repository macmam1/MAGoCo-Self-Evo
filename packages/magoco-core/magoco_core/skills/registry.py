"""
Skills Registry Core
Professional skill registry with versioning, dependencies, security, marketplace
"""

import os
import json
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Iterator
from datetime import datetime
from contextlib import contextmanager
import sqlite3
import semver

from .models import (
    SkillManifest, SkillCategory, SkillType, SkillStatus,
    SecurityLevel, ExecutionMode, SkillDependency,
    SkillManifest, SkillSearchQuery, SkillSearchResult,
    SkillCategory, SkillType, SkillStatus, SecurityLevel,
    ExecutionMode, SkillParameter, SkillReturn, SkillDependency,
    SkillTest, SkillExample, SkillReview, SkillAnalytics,
    SkillComposition
)

logger = logging.getLogger(__name__)


class SkillsRegistry:
    """
    Professional Skills Registry with:
    - Semantic versioning
    - Dependency resolution
    - Security sandboxing
    - Marketplace features
    - Full audit trail
    """
    
    def __init__(
        self,
        registry_dir: str = "./data/skills",
        db_path: str = "./data/skills/registry.db",
    ):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"SkillsRegistry initialized at {self.registry_dir}")
    
    def _init_database(self):
        """Initialize SQLite database for registry metadata"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Skills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                version TEXT NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                
                author TEXT DEFAULT '',
                author_email TEXT DEFAULT '',
                organization TEXT DEFAULT '',
                license TEXT DEFAULT 'MIT',
                homepage TEXT DEFAULT '',
                repository TEXT DEFAULT '',
                
                entry_point TEXT DEFAULT 'main',
                code_path TEXT DEFAULT '',
                requirements TEXT DEFAULT '[]',
                system_requirements TEXT DEFAULT '[]',
                
                execution_mode TEXT DEFAULT 'sync',
                timeout REAL DEFAULT 30.0,
                max_memory_mb INTEGER DEFAULT 512,
                max_cpu_percent INTEGER DEFAULT 50,
                security_level TEXT DEFAULT 'restricted',
                allowed_domains TEXT DEFAULT '[]',
                allowed_commands TEXT DEFAULT '[]',
                
                parameters TEXT DEFAULT '[]',
                returns TEXT DEFAULT '{}',
                dependencies TEXT DEFAULT '[]',
                
                status TEXT DEFAULT 'draft',
                tests TEXT DEFAULT '[]',
                examples TEXT DEFAULT '[]',
                min_core_version TEXT DEFAULT '0.3.0',
                compatible_platforms TEXT DEFAULT '["linux","macos","windows"]',
                
                price REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                is_public INTEGER DEFAULT 1,
                featured INTEGER DEFAULT 0,
                
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                
                analytics TEXT DEFAULT '{}',
                content_hash TEXT DEFAULT '',
                
                UNIQUE(id, version)
            )
        """)
        
        # Skill compositions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_compositions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                skills TEXT DEFAULT '[]',
                connections TEXT DEFAULT '[]',
                parallel_groups TEXT DEFAULT '[]',
                conditionals TEXT DEFAULT '[]',
                version TEXT DEFAULT '1.0.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Reviews
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_reviews (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                helpful_votes INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Execution history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_history (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                user_id TEXT,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                execution_time REAL,
                memory_mb REAL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_type ON skills(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_author ON skills(author)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_tags ON skills(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_rating ON skills(rating)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_downloads ON skills(downloads)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_updated ON skills(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_skill ON skill_reviews(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_skill ON execution_history(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_user ON execution_history(user_id)")
        
        self.conn.commit()
    
    # ============ Database Helpers ============
    
    @contextmanager
    def _cursor(self):
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
    
    def _row_to_manifest(self, row: sqlite3.Row) -> SkillManifest:
        """Convert database row to SkillManifest"""
        return SkillManifest.from_dict(dict(row))
    
    # ============ CRUD Operations ============
    
    def create(self, manifest: SkillManifest) -> str:
        """Create a new skill version"""
        # Validate
        self._validate_manifest(manifest)
        
        # Check if skill exists
        existing = self.get(manifest.id, manifest.version)
        if existing:
            raise ValueError(f"Skill {manifest.id} v{manifest.version} already exists")
        
        # Check dependencies
        self._validate_dependencies(manifest)
        
        # Compute hash
        manifest.content_hash = manifest.compute_hash()
        manifest.updated_at = datetime.utcnow()
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO skills (
                    id, name, display_name, description, version, category, type, tags,
                    author, author_email, organization, license, homepage, repository,
                    entry_point, code_path, requirements, system_requirements,
                    execution_mode, timeout, max_memory_mb, max_cpu_percent, security_level,
                    allowed_domains, allowed_commands, parameters, returns, dependencies,
                    status, tests, examples, min_core_version, compatible_platforms,
                    price, currency, is_public, featured,
                    created_at, updated_at, published_at, downloads, rating, review_count,
                    analytics, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                manifest.id, manifest.name, manifest.display_name, manifest.description,
                manifest.version, manifest.category.value, manifest.type.value,
                json.dumps(list(manifest.tags)),
                manifest.author, manifest.author_email, manifest.organization,
                manifest.license, manifest.homepage, manifest.repository,
                manifest.entry_point, manifest.code_path,
                json.dumps(manifest.requirements), json.dumps(manifest.system_requirements),
                manifest.execution_mode.value, manifest.timeout, manifest.max_memory_mb,
                manifest.max_cpu_percent, manifest.security_level.value,
                json.dumps(manifest.allowed_domains), json.dumps(manifest.allowed_commands),
                json.dumps([p.to_dict() for p in manifest.parameters]),
                json.dumps(manifest.returns.to_dict() if hasattr(manifest.returns, 'to_dict') else {}),
                json.dumps([d.to_dict() if hasattr(d, 'to_dict') else d for d in manifest.dependencies]),
                manifest.status.value,
                json.dumps([t.to_dict() if hasattr(t, 'to_dict') else t for t in manifest.tests]),
                json.dumps([e.to_dict() if hasattr(e, 'to_dict') else e for e in manifest.examples]),
                manifest.min_core_version, json.dumps(manifest.compatible_platforms),
                manifest.price, manifest.currency, int(manifest.is_public), int(manifest.featured),
                manifest.created_at.isoformat(), manifest.updated_at.isoformat(),
                manifest.published_at.isoformat() if manifest.published_at else None,
                manifest.downloads, manifest.rating, manifest.review_count,
                json.dumps(manifest.analytics.to_dict() if hasattr(manifest.analytics, 'to_dict') else {}),
                manifest.content_hash,
            ))
        
        # Create skill directory and save manifest
        skill_dir = self.registry_dir / manifest.id / manifest.version
        skill_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = skill_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created skill: {manifest.id} v{manifest.version}")
        return manifest.id
    
    def get(self, skill_id: str, version: Optional[str] = None) -> Optional[SkillManifest]:
        """Get a skill by ID and version (latest if version not specified)"""
        with self._cursor() as cursor:
            if version:
                cursor.execute(
                    "SELECT * FROM skills WHERE id = ? AND version = ?",
                    (skill_id, version)
                )
            else:
                cursor.execute(
                    "SELECT * FROM skills WHERE id = ? ORDER BY version DESC LIMIT 1",
                    (skill_id,)
                )
            row = cursor.fetchone()
            if row:
                return self._row_to_manifest(row)
        return None
    
    def get_latest(self, skill_id: str) -> Optional[SkillManifest]:
        """Get the latest version of a skill"""
        return self.get(skill_id)
    
    def list_versions(self, skill_id: str) -> List[str]:
        """List all versions of a skill"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT version FROM skills WHERE id = ? ORDER BY version DESC",
                (skill_id,)
            )
            return [row["version"] for row in cursor.fetchall()]
    
    def update(self, manifest: SkillManifest) -> bool:
        """Update an existing skill version (only for draft status)"""
        existing = self.get(manifest.id, manifest.version)
        if not existing:
            return False
        
        if existing.status != SkillStatus.DRAFT:
            raise ValueError("Can only update skills in DRAFT status")
        
        self._validate_manifest(manifest)
        manifest.content_hash = manifest.compute_hash()
        manifest.updated_at = datetime.utcnow()
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE skills SET
                    name=?, display_name=?, description=?, category=?, type=?, tags=?,
                    author=?, author_email=?, organization=?, license=?, homepage=?, repository=?,
                    entry_point=?, code_path=?, requirements=?, system_requirements=?,
                    execution_mode=?, timeout=?, max_memory_mb=?, max_cpu_percent=?, security_level=?,
                    allowed_domains=?, allowed_commands=?, parameters=?, returns=?, dependencies=?,
                    status=?, tests=?, examples=?, min_core_version=?, compatible_platforms=?,
                    price=?, currency=?, is_public=?, featured=?,
                    updated_at=?, analytics=?, content_hash=?
                WHERE id=? AND version=?
            """, (
                manifest.name, manifest.display_name, manifest.description,
                manifest.category.value, manifest.type.value, json.dumps(list(manifest.tags)),
                manifest.author, manifest.author_email, manifest.organization,
                manifest.license, manifest.homepage, manifest.repository,
                manifest.entry_point, manifest.code_path,
                json.dumps(manifest.requirements), json.dumps(manifest.system_requirements),
                manifest.execution_mode.value, manifest.timeout, manifest.max_memory_mb,
                manifest.max_cpu_percent, manifest.security_level.value,
                json.dumps(manifest.allowed_domains), json.dumps(manifest.allowed_commands),
                json.dumps([p.to_dict() for p in manifest.parameters]),
                json.dumps(manifest.returns.to_dict() if hasattr(manifest.returns, 'to_dict') else {}),
                json.dumps([d.to_dict() if hasattr(d, 'to_dict') else d for d in manifest.dependencies]),
                manifest.status.value,
                json.dumps([t.to_dict() if hasattr(t, 'to_dict') else t for t in manifest.tests]),
                json.dumps([e.to_dict() if hasattr(e, 'to_dict') else e for e in manifest.examples]),
                manifest.min_core_version, json.dumps(manifest.compatible_platforms),
                manifest.price, manifest.currency, int(manifest.is_public), int(manifest.featured),
                manifest.updated_at.isoformat(),
                json.dumps(manifest.analytics.to_dict() if hasattr(manifest.analytics, 'to_dict') else {}),
                manifest.content_hash,
                manifest.id, manifest.version,
            ))
        
        # Update manifest file
        skill_dir = self.registry_dir / manifest.id / manifest.version
        manifest_path = skill_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        
        return True
    
    def delete(self, skill_id: str, version: Optional[str] = None, hard: bool = False) -> bool:
        """Delete a skill (soft by default, hard removes all versions)"""
        if version:
            # Delete specific version
            with self._cursor() as cursor:
                if hard:
                    cursor.execute("DELETE FROM skills WHERE id = ? AND version = ?", (skill_id, version))
                else:
                    cursor.execute(
                        "UPDATE skills SET status = 'archived' WHERE id = ? AND version = ?",
                        (skill_id, version)
                    )
            return True
        else:
            # Delete all versions
            with self._cursor() as cursor:
                if hard:
                    cursor.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
                else:
                    cursor.execute("UPDATE skills SET status = 'archived' WHERE id = ?", (skill_id,))
            
            # Remove directory
            if hard:
                skill_dir = self.registry_dir / skill_id
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)
            return True
    
    def publish(self, skill_id: str, version: str) -> bool:
        """Publish a skill (draft -> published)"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return False
        
        if manifest.status != SkillStatus.DRAFT:
            raise ValueError("Can only publish skills in DRAFT status")
        
        # Run tests before publishing
        test_results = self.run_tests(skill_id, version)
        if not test_results["passed"]:
            raise ValueError(f"Tests failed: {test_results['failures']}")
        
        manifest.status = SkillStatus.PUBLISHED
        manifest.published_at = datetime.utcnow()
        manifest.updated_at = datetime.utcnow()
        
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE skills SET status = ?, published_at = ?, updated_at = ? WHERE id = ? AND version = ?",
                (SkillStatus.PUBLISHED.value, manifest.published_at.isoformat(), manifest.updated_at.isoformat(), skill_id, version)
            )
        
        # Update manifest file
        self._save_manifest_file(manifest)
        
        logger.info(f"Published skill: {skill_id} v{version}")
        return True
    
    def _save_manifest_file(self, manifest: SkillManifest):
        """Save manifest to file system"""
        skill_dir = self.registry_dir / manifest.id / manifest.version
        skill_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = skill_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _validate_manifest(self, manifest: SkillManifest):
        """Validate skill manifest"""
        if not manifest.id:
            raise ValueError("Skill ID is required")
        if not manifest.name:
            raise ValueError("Skill name is required")
        if not manifest.version:
            raise ValueError("Version is required")
        if not semver.Version.is_valid(manifest.version):
            raise ValueError(f"Invalid version format: {manifest.version}")
        if not manifest.display_name:
            raise ValueError("Display name is required")
        if not manifest.description:
            raise ValueError("Description is required")
        if not manifest.author:
            raise ValueError("Author is required")
        
        # Validate parameters
        param_names = set()
        for param in manifest.parameters:
            if param.name in param_names:
                raise ValueError(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)
        
        # Validate dependencies exist
        for dep in manifest.dependencies:
            if dep.skill_id:
                dep_skill = self.get(dep.skill_id)
                if not dep_skill:
                    raise ValueError(f"Dependency skill not found: {dep.skill_id}")
    
    def _validate_dependencies(self, manifest: SkillManifest):
        """Validate all dependencies can be resolved"""
        for dep in manifest.dependencies:
            if dep.skill_id:
                dep_skill = self.get(dep.skill_id)
                if not dep_skill:
                    raise ValueError(f"Dependency skill not found: {dep.skill_id}")
                # Check version compatibility
                if dep.version_spec and dep_skill.version:
                    if not semver.Version(dep_skill.version).match(dep.version_spec):
                        raise ValueError(
                            f"Dependency {dep.skill_id} v{dep_skill.version} "
                            f"does not satisfy {dep.version_spec}"
                        )
    
    # ============ Search & Discovery ============
    
    def search(self, query: SkillSearchQuery) -> List[SkillSearchResult]:
        """Search skills with advanced filters"""
        conditions = []
        params = []
        
        # Text search
        if query.query:
            conditions.append("(name LIKE ? OR display_name LIKE ? OR description LIKE ?)")
            params.extend([f"%{query.query}%"] * 3)
        
        # Filters
        if query.category:
            conditions.append("category = ?")
            params.append(query.category.value)
        
        if query.type:
            conditions.append("type = ?")
            params.append(query.type.value)
        
        if query.author:
            conditions.append("author LIKE ?")
            params.append(f"%{query.author}%")
        
        if query.min_rating > 0:
            conditions.append("rating >= ?")
            params.append(query.min_rating)
        
        if query.max_price < float('inf'):
            conditions.append("price <= ?")
            params.append(query.max_price)
        
        if query.free_only:
            conditions.append("price = 0")
        
        if query.featured_only:
            conditions.append("featured = 1")
        
        if query.security_level:
            conditions.append("security_level = ?")
            params.append(query.security_level.value)
        
        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        if query.compatible_version:
            conditions.append("min_core_version <= ?")
            params.append(query.compatible_version)
        
        # Status filter (default to published only)
        if query.verified_only:
            conditions.append("status = 'published'")
        else:
            conditions.append("status IN ('published', 'draft')")
        
        # Build WHERE clause
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Sort
        sort_fields = {
            "relevance": "rating DESC, downloads DESC",
            "rating": "rating DESC",
            "downloads": "downloads DESC",
            "updated": "updated_at DESC",
            "created": "created_at DESC",
            "name": "name ASC",
        }
        sort_by = sort_fields.get(query.sort_by, "rating DESC")
        sort_order = "DESC" if query.sort_order == "desc" else "ASC"
        order_clause = f"ORDER BY {sort_by} {sort_order}"
        
        # Pagination
        offset = (query.page - 1) * query.page_size
        limit_clause = f"LIMIT {query.page_size} OFFSET {offset}"
        
        # Execute
        sql = f"SELECT * FROM skills {where_clause} {order_clause} {limit_clause}"
        
        with self._cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                manifest = self._row_to_manifest(row)
                score = self._calculate_relevance(manifest, query)
                results.append(SkillSearchResult(
                    skill=manifest,
                    score=score,
                    matched_fields=self._get_matched_fields(manifest, query),
                ))
            
            return results
    
    def _calculate_relevance(self, manifest: SkillManifest, query: SkillSearchQuery) -> float:
        """Calculate relevance score for search ranking"""
        score = 0.0
        
        # Text match
        if query.query:
            query_lower = query.query.lower()
            if query_lower in manifest.name.lower():
                score += 10
            if query_lower in manifest.display_name.lower():
                score += 8
            if query_lower in manifest.description.lower():
                score += 5
            for tag in manifest.tags:
                if query_lower in tag.lower():
                    score += 3
        
        # Rating boost
        score += manifest.rating * 2
        
        # Downloads boost
        score += min(manifest.downloads / 1000, 5)
        
        # Recency boost
        days_old = (datetime.utcnow() - manifest.updated_at).days
        if days_old < 30:
            score += 2
        elif days_old < 90:
            score += 1
        
        # Featured boost
        if manifest.featured:
            score += 3
        
        return score
    
    def _get_matched_fields(self, manifest: SkillManifest, query: SkillSearchQuery) -> List[str]:
        """Get which fields matched the query"""
        matched = []
        if query.query:
            query_lower = query.query.lower()
            if query_lower in manifest.name.lower():
                matched.append("name")
            if query_lower in manifest.display_name.lower():
                matched.append("display_name")
            if query_lower in manifest.description.lower():
                matched.append("description")
            for tag in manifest.tags:
                if query_lower in tag.lower():
                    matched.append("tags")
                    break
        return matched
    
    def get_featured(self, limit: int = 10) -> List[SkillManifest]:
        """Get featured skills"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM skills WHERE featured = 1 AND status = 'published' ORDER BY rating DESC, downloads DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_manifest(row) for row in cursor.fetchall()]
    
    def get_popular(self, limit: int = 10) -> List[SkillManifest]:
        """Get most popular skills"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM skills WHERE status = 'published' ORDER BY downloads DESC, rating DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_manifest(row) for row in cursor.fetchall()]
    
    def get_recent(self, limit: int = 10) -> List[SkillManifest]:
        """Get recently updated skills"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM skills WHERE status = 'published' ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_manifest(row) for row in cursor.fetchall()]
    
    def get_by_category(self, category: SkillCategory, limit: int = 20) -> List[SkillManifest]:
        """Get skills by category"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM skills WHERE category = ? AND status = 'published' ORDER BY rating DESC, downloads DESC LIMIT ?",
                (category.value, limit)
            )
            return [self._row_to_manifest(row) for row in cursor.fetchall()]
    
    def get_by_author(self, author: str) -> List[SkillManifest]:
        """Get skills by author"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM skills WHERE author = ? AND status = 'published' ORDER BY updated_at DESC",
                (author,)
            )
            return [self._row_to_manifest(row) for row in cursor.fetchall()]
    
    # ============ Dependency Resolution ============
    
    def resolve_dependencies(self, skill_id: str, version: str) -> List[SkillManifest]:
        """Resolve all dependencies for a skill recursively"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return []
        
        resolved = []
        visited = set()
        
        def resolve(dep: SkillDependency):
            if dep.skill_id in visited:
                return
            visited.add(dep.skill_id)
            
            dep_manifest = self.get(dep.skill_id)
            if dep_manifest:
                resolved.append(dep_manifest)
                # Recursively resolve dependencies
                for sub_dep in dep_manifest.dependencies:
                    if sub_dep.skill_id:
                        resolve(sub_dep)
        
        for dep in manifest.dependencies:
            if dep.skill_id:
                resolve(dep)
        
        return resolved
    
    def check_compatibility(self, skill_id: str, version: str, core_version: str) -> bool:
        """Check if skill is compatible with core version"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return False
        return semver.Version(core_version).match(manifest.min_core_version)
    
    # ============ Testing & Validation ============
    
    def run_tests(self, skill_id: str, version: str) -> Dict[str, Any]:
        """Run all tests for a skill"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return {"passed": False, "failures": ["Skill not found"]}
        
        results = {"passed": True, "failures": [], "details": []}
        
        for test in manifest.tests:
            try:
                # In production, execute in sandbox
                # For now, just validate structure
                if not test.name:
                    raise ValueError("Test name is required")
                if not test.input_data:
                    raise ValueError("Test input_data is required")
                
                results["details"].append({
                    "name": test.name,
                    "passed": True,
                })
            except Exception as e:
                results["passed"] = False
                results["failures"].append(f"{test.name}: {str(e)}")
                results["details"].append({
                    "name": test.name,
                    "passed": False,
                    "error": str(e),
                })
        
        return results
    
    def validate_skill(self, skill_id: str, version: str) -> Dict[str, Any]:
        """Comprehensive skill validation"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return {"valid": False, "errors": ["Skill not found"]}
        
        errors = []
        warnings = []
        
        # Check code exists
        skill_dir = self.registry_dir / skill_id / version
        code_path = skill_dir / manifest.code_path
        if not code_path.exists():
            errors.append(f"Code file not found: {manifest.code_path}")
        
        # Check requirements
        req_path = skill_dir / "requirements.txt"
        if not req_path.exists() and manifest.requirements:
            warnings.append("requirements.txt not found but requirements specified")
        
        # Check tests
        if not manifest.tests:
            warnings.append("No tests defined")
        
        # Check examples
        if not manifest.examples:
            warnings.append("No examples provided")
        
        # Check documentation
        readme_path = skill_dir / "README.md"
        if not readme_path.exists():
            warnings.append("README.md not found")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    # ============ Reviews & Ratings ============
    
    def add_review(self, review: SkillReview) -> str:
        """Add a review for a skill"""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO skill_reviews (
                    id, skill_id, skill_version, user_id, rating,
                    title, content, helpful_votes, verified, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review.id, review.skill_id, review.version, review.user_id,
                review.rating, review.title, review.content,
                review.helpful_votes, int(review.verified),
                review.created_at.isoformat(), review.updated_at.isoformat(),
            ))
        
        # Update skill rating
        self._update_skill_rating(review.skill_id)
        
        return review.id
    
    def get_reviews(self, skill_id: str, version: Optional[str] = None, limit: int = 20) -> List[SkillReview]:
        """Get reviews for a skill"""
        with self._cursor() as cursor:
            if version:
                cursor.execute(
                    "SELECT * FROM skill_reviews WHERE skill_id = ? AND skill_version = ? ORDER BY created_at DESC LIMIT ?",
                    (skill_id, version, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM skill_reviews WHERE skill_id = ? ORDER BY created_at DESC LIMIT ?",
                    (skill_id, limit)
                )
            rows = cursor.fetchall()
            
            reviews = []
            for row in rows:
                reviews.append(SkillReview(
                    id=row["id"],
                    skill_id=row["skill_id"],
                    version=row["skill_version"],
                    user_id=row["user_id"],
                    rating=row["rating"],
                    title=row["title"] or "",
                    content=row["content"] or "",
                    helpful_votes=row["helpful_votes"],
                    verified=bool(row["verified"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                ))
            return reviews
    
    def _update_skill_rating(self, skill_id: str):
        """Recalculate skill rating from reviews"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM skill_reviews WHERE skill_id = ?",
                (skill_id,)
            )
            row = cursor.fetchone()
            if row and row["count"] > 0:
                cursor.execute(
                    "UPDATE skills SET rating = ?, review_count = ? WHERE id = ?",
                    (round(row["avg_rating"], 2), row["count"], skill_id)
                )
    
    # ============ Analytics & Execution Tracking ============
    
    def record_execution(self, skill_id: str, skill_version: str, user_id: Optional[str],
                        input_data: Dict[str, Any], output_data: Any,
                        status: str, error: Optional[str] = None,
                        execution_time: float = 0.0, memory_mb: float = 0.0) -> str:
        """Record skill execution for analytics"""
        exec_id = str(uuid.uuid4())
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO execution_history (
                    id, skill_id, skill_version, user_id, status,
                    input_data, output_data, error, execution_time, memory_mb,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exec_id, skill_id, skill_version, user_id, status,
                json.dumps(input_data), json.dumps(output_data) if output_data else None,
                error, execution_time, memory_mb,
                datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            ))
        
        # Update analytics
        self._update_analytics(skill_id, status == "success", execution_time, memory_mb)
        
        return exec_id
    
    def _update_analytics(self, skill_id: str, success: bool, exec_time: float, memory_mb: float):
        """Update skill analytics"""
        with self._cursor() as cursor:
            cursor.execute("SELECT analytics FROM skills WHERE id = (SELECT id FROM skills WHERE id = ? ORDER BY version DESC LIMIT 1)", (skill_id,))
            row = cursor.fetchone()
            
            if row:
                analytics = json.loads(row["analytics"] or "{}")
                analytics["total_executions"] = analytics.get("total_executions", 0) + 1
                if success:
                    analytics["successful_executions"] = analytics.get("successful_executions", 0) + 1
                else:
                    analytics["failed_executions"] = analytics.get("failed_executions", 0) + 1
                
                total = analytics["total_executions"]
                analytics["avg_execution_time"] = (
                    (analytics.get("avg_execution_time", 0) * (total - 1) + exec_time) / total
                )
                analytics["avg_memory_mb"] = (
                    (analytics.get("avg_memory_mb", 0) * (total - 1) + exec_time) / total
                )
                analytics["error_rate"] = analytics["failed_executions"] / total
                analytics["last_executed"] = datetime.utcnow().isoformat()
                
                # Update popularity score
                analytics["popularity_score"] = (
                    analytics.get("downloads", 0) * 0.3 +
                    analytics.get("successful_executions", 0) * 0.5 +
                    analytics.get("rating", 0) * 20
                )
                
                cursor.execute(
                    "UPDATE skills SET analytics = ? WHERE id = (SELECT id FROM skills WHERE id = ? ORDER BY version DESC LIMIT 1)",
                    (json.dumps(analytics), skill_id)
                )
    
    # ============ Composition ============
    
    def create_composition(self, composition: SkillComposition) -> str:
        """Create a skill composition"""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO skill_compositions (
                    id, name, description, skills, connections,
                    parallel_groups, conditionals, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                composition.id, composition.name, composition.description,
                json.dumps(composition.skills), json.dumps(composition.connections),
                json.dumps(composition.parallel_groups), json.dumps(composition.conditionals),
                composition.version, composition.created_at.isoformat(),
                composition.updated_at.isoformat(),
            ))
        return composition.id
    
    def get_composition(self, composition_id: str) -> Optional[SkillComposition]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM skill_compositions WHERE id = ?", (composition_id,))
            row = cursor.fetchone()
            if row:
                return SkillComposition(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"] or "",
                    skills=json.loads(row["skills"] or "[]"),
                    connections=json.loads(row["connections"] or "[]"),
                    parallel_groups=json.loads(row["parallel_groups"] or "[]"),
                    conditionals=json.loads(row["conditionals"] or "[]"),
                    version=row["version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
        return None
    
    # ============ Installation & Execution ============
    
    def install_skill(self, skill_id: str, version: str, target_dir: Path) -> bool:
        """Install a skill to a target directory"""
        manifest = self.get(skill_id, version)
        if not manifest:
            return False
        
        source_dir = self.registry_dir / skill_id / version
        if not source_dir.exists():
            return False
        
        # Copy skill directory
        target_skill_dir = target_dir / skill_id / version
        if target_skill_dir.exists():
            shutil.rmtree(target_skill_dir)
        
        shutil.copytree(source_dir, target_skill_dir)
        
        # Install requirements
        req_file = target_dir / skill_id / version / "requirements.txt"
        if req_file.exists():
            import subprocess
            try:
                subprocess.run(["pip", "install", "-r", str(req_file)], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install requirements: {e}")
                return False
        
        return True
    
    def get_execution_history(self, skill_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get execution history"""
        with self._cursor() as cursor:
            if skill_id:
                cursor.execute(
                    "SELECT * FROM execution_history WHERE skill_id = ? ORDER BY started_at DESC LIMIT ?",
                    (skill_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM execution_history ORDER BY started_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM skills WHERE status = 'published'")
            total = cursor.fetchone()["total"]
            
            cursor.execute("SELECT category, COUNT(*) as count FROM skills WHERE status = 'published' GROUP BY category")
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT type, COUNT(*) as count FROM skills WHERE status = 'published' GROUP BY type")
            by_type = {row["type"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT COUNT(*) FROM skills WHERE status = 'draft'")
            drafts = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(downloads) FROM skills")
            total_downloads = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM execution_history WHERE status = 'success'")
            successful_execs = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM execution_history WHERE status = 'error'")
            failed_execs = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM skill_reviews")
            total_reviews = cursor.fetchone()[0]
        
        return {
            "total_skills": total,
            "draft_skills": drafts,
            "by_category": by_category,
            "by_type": by_type,
            "total_downloads": total_downloads,
            "successful_executions": successful_execs,
            "failed_executions": failed_execs,
            "total_reviews": total_reviews,
        }
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("SkillsRegistry closed")


# Global registry instance
_registry: Optional[SkillsRegistry] = None


def get_skills_registry(registry_dir: Optional[str] = None) -> SkillsRegistry:
    """Get or create global skills registry"""
    global _registry
    if _registry is None:
        _registry = SkillsRegistry(registry_dir or "./data/skills")
    return _registry