# Estimated Data Volume for 3 Months of CourtListener Data

Based on typical CourtListener data patterns and API documentation, here's an estimate for downloading 3 months of data from all 6 target courts:

## Courts of Interest
1. **District of Delaware (ded)** - High patent litigation volume
2. **Eastern District of Texas (txed)** - Highest patent litigation volume
3. **Northern District of California (cand)** - Tech hub litigation
4. **Court of Appeals for the Federal Circuit (cafc)** - Patent appeals
5. **Central District of California (cacd)** - Large general caseload
6. **Southern District of New York (nysd)** - Financial and IP litigation

## Estimated Data Volume (3 Months)

### Per Court Estimates (High-Volume District Court)

**Eastern District of Texas (txed)** - Example:
- **Dockets**: ~2,500-3,500 cases
- **Docket Entries**: ~25,000-35,000 entries
- **RECAP Documents**: ~50,000-75,000 documents
  - Transcripts: ~500-1,500 (1-2% of documents)
- **Opinions**: ~500-1,000
- **Audio**: ~50-100 recordings

### Total Estimates (All 6 Courts)

**Document Counts:**
- **Dockets**: ~12,000-18,000 cases
- **Docket Entries**: ~120,000-180,000 entries  
- **RECAP Documents**: ~250,000-400,000 documents
  - **Estimated Transcripts**: ~2,500-7,500 documents
- **Opinions**: ~2,500-5,000
- **Audio Recordings**: ~200-500

**Storage Requirements:**

1. **JSON Metadata Only** (what we'll download):
   - Dockets: ~100-150 MB
   - Opinions: ~150-250 MB
   - RECAP metadata: ~1.5-2.5 GB
   - Audio metadata: ~2-5 MB
   - **Total JSON: ~2-3 GB**

2. **PostgreSQL Storage** (after loading):
   - With indexes and overhead: **~4-6 GB**

3. **If downloading PDFs** (NOT recommended initially):
   - Average PDF: 200KB-2MB
   - Total PDFs: **50-400 GB**

**API Call Requirements:**
- Estimated API calls: ~100,000-150,000
- Time at rate limit (4,500/hour): **22-33 hours**
- Can be run incrementally over several days

## Transcript-Specific Estimates

**Expected Transcript Documents: 2,500-7,500**

Types of transcripts likely to find:
- **Depositions**: 30-40% (~1,000-3,000)
- **Hearings**: 25-30% (~750-2,250)
- **Trial transcripts**: 15-20% (~375-1,500)
- **Oral arguments**: 10-15% (~250-1,125)
- **Status conferences**: 10-15% (~250-1,125)
- **Other**: 5-10% (~125-750)

**Transcript Characteristics:**
- Average pages: 50-200 pages
- With text extraction: 10-30% have plain text
- Requiring OCR: 70-90% need PDF processing

## Recommendations

### Phase 1: Metadata Only (Recommended First Step)
1. Download JSON metadata for all courts (~2-3 GB)
2. Load into PostgreSQL for analysis
3. Identify high-value transcripts
4. Total time: 1-2 days running intermittently

### Phase 2: Selective PDF Download
1. Download PDFs only for identified transcripts
2. Implement OCR pipeline for text extraction
3. Storage needed: 5-20 GB for transcript PDFs

### Bandwidth Considerations
- JSON download: ~2-3 GB total
- Rate limited by API, not bandwidth
- Can pause/resume as needed

## Sample Download Commands

```bash
# Test with Delaware (smallest) for 30 days
python3 bulk_download_enhanced.py --courts ded --days 30

# All courts, metadata only, 90 days
python3 bulk_download_enhanced.py --days 90

# Transcripts only from high-volume courts
python3 bulk_download_enhanced.py \
    --courts txed cand nysd \
    --days 90 \
    --transcripts-only

# High priority courts with all data
python3 bulk_download_enhanced.py \
    --high-priority-only \
    --days 90
```

## Summary

**For 3 months of data from all 6 courts:**
- **Download size**: 2-3 GB (JSON metadata)
- **Database size**: 4-6 GB (with indexes)
- **Time required**: 22-33 hours (can be interrupted)
- **Transcripts found**: 2,500-7,500 documents
- **Cost**: Free (with API token)

This is very manageable for an initial analysis phase. The JSON metadata alone will let you identify valuable transcripts and extended dialogue without committing to massive PDF downloads.