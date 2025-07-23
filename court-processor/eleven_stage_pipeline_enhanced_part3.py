# Part 3 of eleven_stage_pipeline_enhanced.py
# Fixed methods and type-specific verification

    def _extract_judge_from_content_fixed(self, content: str) -> Optional[str]:
        """Extract judge name from document content with fixed patterns"""
        if not content:
            return None
        
        # Fixed judge patterns - more specific to avoid greedy matching
        patterns = [
            # Standard patterns (working well)
            r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'Before:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'JUDGE:\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'Signed\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            
            # Fixed patterns for all-caps names
            r'([A-Z]+\s+[A-Z]\.\s+[A-Z]+)(?:,\s+Chief)?\s+(?:United States\s+)?District Judge',  # JOHN A. SMITH
            r'([A-Z]+\s+[A-Z]+)(?:,\s+Chief)?\s+(?:United States\s+)?District Judge',  # JOHN SMITH
            
            # Opinion-specific patterns
            r'Opinion by:\s*([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+J\.',  # "Smith, J."
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+Circuit Judge',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+dissenting',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+concurring',
        ]
        
        # Search in first 2000 characters and last 1000
        content_start = content[:2000]
        content_end = content[-1000:] if len(content) > 1000 else ""
        
        for pattern in patterns:
            # Check start
            match = re.search(pattern, content_start)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                
                # Validate it's actually a name (not all caps like "UNITED STATES DISTRICT")
                if judge_name and not judge_name.isupper() or \
                   (judge_name.isupper() and ' ' in judge_name and len(judge_name.split()) <= 4):
                    logger.info(f"  Extracted judge from content start: {judge_name}")
                    return judge_name
            
            # Check end
            match = re.search(pattern, content_end)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                
                # Validate it's actually a name
                if judge_name and not judge_name.isupper() or \
                   (judge_name.isupper() and ' ' in judge_name and len(judge_name.split()) <= 4):
                    logger.info(f"  Extracted judge from content end: {judge_name}")
                    return judge_name
        
        return None
    
    def _verify_pipeline_results_by_type(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced pipeline verification with document type breakdown"""
        # Overall verification
        overall_verification = self._verify_pipeline_results_validated(documents)
        
        # Type-specific verification
        type_metrics = {}
        for doc_type in ['opinion', 'docket', 'order', 'transcript', 'unknown']:
            type_docs = [d for d in documents if d.get('detected_type') == doc_type]
            if type_docs:
                type_metrics[doc_type] = self._calculate_type_metrics(type_docs)
        
        # Enhanced verification result
        verification = {
            'overall': overall_verification,
            'by_document_type': type_metrics,
            'type_distribution': self.document_type_stats,
            'insights': self._generate_insights(type_metrics)
        }
        
        # Log type-specific performance
        logger.info("\nDocument Type Performance:")
        for doc_type, metrics in type_metrics.items():
            logger.info(f"\n{doc_type.upper()}:")
            logger.info(f"  Documents: {metrics.get('total', 0)}")
            logger.info(f"  Completeness: {metrics.get('completeness_score', 0):.1f}%")
            logger.info(f"  Quality: {metrics.get('quality_score', 0):.1f}%")
        
        return verification
    
    def _calculate_type_metrics(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics for a specific document type"""
        metrics = {
            'total': len(documents),
            'courts_resolved': 0,
            'judges_found': 0,
            'citations_found': 0,
            'keywords_extracted': 0,
            'completeness_score': 0,
            'quality_score': 0
        }
        
        total_completeness = 0
        total_quality = 0
        
        for doc in documents:
            doc_completeness = 0
            doc_quality = 0
            max_possible = 6  # 6 enhancement types
            
            # Court resolution
            if doc.get('court_enhancement', {}).get('resolved'):
                metrics['courts_resolved'] += 1
                doc_completeness += 1
                doc_quality += 2 if not doc.get('court_enhancement', {}).get('validation', {}).get('errors') else 1
            
            # Judge identification
            if doc.get('judge_enhancement', {}).get('enhanced') or \
               doc.get('judge_enhancement', {}).get('judge_name_found'):
                metrics['judges_found'] += 1
                doc_completeness += 1
                doc_quality += 2
            
            # Citations
            if doc.get('citations_extracted', {}).get('count', 0) > 0:
                metrics['citations_found'] += 1
                doc_completeness += 1
                doc_quality += 1
            
            # Keywords
            if len(doc.get('keyword_extraction', {}).get('keywords', [])) > 0:
                metrics['keywords_extracted'] += 1
                doc_completeness += 1
                doc_quality += 1
            
            # Structure and reporters
            if doc.get('structure_analysis', {}).get('sections', 0) > 0:
                doc_completeness += 1
                doc_quality += 1
            
            if doc.get('reporters_normalized', {}).get('normalized_count', 0) > 0:
                doc_completeness += 1
                doc_quality += 1
            
            total_completeness += (doc_completeness / max_possible)
            total_quality += (doc_quality / 10)  # Max quality points = 10
        
        if metrics['total'] > 0:
            metrics['completeness_score'] = (total_completeness / metrics['total']) * 100
            metrics['quality_score'] = (total_quality / metrics['total']) * 100
            metrics['court_resolution_rate'] = (metrics['courts_resolved'] / metrics['total']) * 100
            metrics['judge_identification_rate'] = (metrics['judges_found'] / metrics['total']) * 100
        
        return metrics
    
    def _generate_insights(self, type_metrics: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate insights from type-specific metrics"""
        insights = []
        
        # Find best and worst performing document types
        if type_metrics:
            best_type = max(type_metrics.items(), 
                          key=lambda x: x[1].get('completeness_score', 0))
            worst_type = min(type_metrics.items(), 
                           key=lambda x: x[1].get('completeness_score', 0))
            
            if best_type[0] != worst_type[0]:
                insights.append(
                    f"{best_type[0].capitalize()} documents have the highest completeness "
                    f"({best_type[1]['completeness_score']:.1f}%) while {worst_type[0]} documents "
                    f"have the lowest ({worst_type[1]['completeness_score']:.1f}%)"
                )
            
            # Check for specific issues
            for doc_type, metrics in type_metrics.items():
                if metrics.get('total', 0) > 0:
                    if metrics.get('court_resolution_rate', 0) < 50:
                        insights.append(
                            f"{doc_type.capitalize()} documents have low court resolution rate "
                            f"({metrics['court_resolution_rate']:.1f}%) - may need specialized extraction"
                        )
                    
                    if metrics.get('judge_identification_rate', 0) < 30:
                        insights.append(
                            f"{doc_type.capitalize()} documents have low judge identification rate "
                            f"({metrics['judge_identification_rate']:.1f}%) - check metadata fields"
                        )
        
        return insights
    
    # Include all the methods from the robust pipeline that we're reusing
    def _fetch_documents(self, limit: int, source_table: str) -> List[Dict[str, Any]]:
        """Stage 1: Fetch documents from database with validation"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Validate table name to prevent SQL injection
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$', source_table):
                    raise ValidationError(f"Invalid table name: {source_table}")
                
                if source_table == 'public.court_documents':
                    cursor.execute("""
                        SELECT id, case_number, document_type, content, metadata, created_at
                        FROM public.court_documents
                        WHERE content IS NOT NULL AND LENGTH(content) > 100
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                else:
                    # For other tables, use parameterized query
                    schema, table = source_table.split('.')
                    cursor.execute("""
                        SELECT * FROM %s.%s
                        WHERE content IS NOT NULL
                        LIMIT %s
                    """, (AsIs(schema), AsIs(table), limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            raise DatabaseConnectionError(
                f"Database query failed: {str(e)}",
                stage="Document Retrieval"
            )