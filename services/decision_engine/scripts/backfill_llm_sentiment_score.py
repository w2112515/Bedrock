"""
Backfill llm_sentiment_score for historical signals.

This script converts llm_sentiment (BULLISH/BEARISH/NEUTRAL) to numerical scores (0-100)
for signals that have llm_sentiment but no llm_sentiment_score.

⚠️ Important Notes:
- Historical data uses default confidence=50 for conversion
- This may differ from the actual confidence values returned by LLM API
- New signals will use real confidence values from LLM API responses

Usage:
    # Dry run (preview only, no changes)
    docker-compose exec decision_engine python services/decision_engine/scripts/backfill_llm_sentiment_score.py --dry-run
    
    # Execute backfill
    docker-compose exec decision_engine python services/decision_engine/scripts/backfill_llm_sentiment_score.py
    
    # Execute with custom batch size
    docker-compose exec decision_engine python services/decision_engine/scripts/backfill_llm_sentiment_score.py --batch-size 500
"""
import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.decision_engine.app.core.database import SessionLocal
from services.decision_engine.app.models.signal import Signal
from services.decision_engine.app.engines.arbiter import DecisionArbiter
from sqlalchemy import func


def backfill_llm_sentiment_score(dry_run: bool = False, batch_size: int = 1000):
    """
    Backfill llm_sentiment_score for signals with llm_sentiment but no llm_sentiment_score.
    
    Args:
        dry_run: If True, only preview changes without committing
        batch_size: Number of signals to process in each batch
    """
    db = SessionLocal()
    arbiter = DecisionArbiter()
    
    try:
        # Query signals that need backfilling
        query = db.query(Signal).filter(
            Signal.llm_sentiment.isnot(None),
            Signal.llm_sentiment_score.is_(None)
        )
        
        total_count = query.count()
        
        if total_count == 0:
            print("✅ No signals need backfilling")
            return
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Found {total_count} signals to backfill")
        print(f"Batch size: {batch_size}")
        print(f"Estimated batches: {(total_count + batch_size - 1) // batch_size}")
        print("")
        
        # Get sentiment distribution
        sentiment_dist = db.query(
            Signal.llm_sentiment,
            func.count(Signal.id).label('count')
        ).filter(
            Signal.llm_sentiment.isnot(None),
            Signal.llm_sentiment_score.is_(None)
        ).group_by(Signal.llm_sentiment).all()
        
        print("Sentiment distribution:")
        for sentiment, count in sentiment_dist:
            print(f"  {sentiment}: {count} signals")
        print("")
        
        if dry_run:
            print("Preview of score conversion (using default confidence=50):")
            for sentiment, _ in sentiment_dist:
                score = arbiter.convert_sentiment_to_score(sentiment, confidence=50.0)
                print(f"  {sentiment} → {score:.2f}")
            print("")
            print("⚠️ This is a DRY RUN. No changes will be made.")
            print("Remove --dry-run flag to execute backfill.")
            return
        
        # Confirm before proceeding (skip in non-interactive mode)
        if sys.stdin.isatty():
            print("⚠️ WARNING: This will modify the database.")
            print("⚠️ Historical data will use default confidence=50 for conversion.")
            print("⚠️ Make sure you have a database backup before proceeding.")
            print("")
            response = input("Continue? (yes/no): ")

            if response.lower() != 'yes':
                print("❌ Backfill cancelled by user")
                return
        else:
            print("⚠️ Running in non-interactive mode, proceeding with backfill...")
        
        print("")
        print("Starting backfill...")
        start_time = datetime.now()
        
        # Backfill in batches
        processed = 0
        for offset in range(0, total_count, batch_size):
            batch = query.limit(batch_size).offset(offset).all()
            
            for signal in batch:
                # Use default confidence=50 for historical data
                llm_score = arbiter.convert_sentiment_to_score(
                    sentiment=signal.llm_sentiment,
                    confidence=50.0
                )
                signal.llm_sentiment_score = llm_score
                processed += 1
            
            db.commit()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_count - processed) / rate if rate > 0 else 0
            
            print(f"Progress: {processed}/{total_count} ({processed/total_count*100:.1f}%) | "
                  f"Rate: {rate:.1f} signals/sec | ETA: {eta:.0f}s")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("")
        print(f"✅ Backfill completed successfully")
        print(f"Total signals processed: {processed}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Average rate: {processed/duration:.1f} signals/sec")
        
        # Verify results
        print("")
        print("Verification:")
        remaining = db.query(Signal).filter(
            Signal.llm_sentiment.isnot(None),
            Signal.llm_sentiment_score.is_(None)
        ).count()

        if remaining == 0:
            print("✅ All signals with llm_sentiment now have llm_sentiment_score")
        else:
            print(f"⚠️ Warning: {remaining} signals still missing llm_sentiment_score")

    except Exception as e:
        db.rollback()
        print(f"❌ Backfill failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill llm_sentiment_score for historical signals')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without committing')
    parser.add_argument('--batch-size', type=int, default=1000, help='Number of signals per batch (default: 1000)')

    args = parser.parse_args()

    backfill_llm_sentiment_score(dry_run=args.dry_run, batch_size=args.batch_size)

