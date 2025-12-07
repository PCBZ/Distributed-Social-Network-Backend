#!/usr/bin/env python3
"""
Multi-Author Post Consistency Test
Tests consistency when multiple authors send posts concurrently:
- User 5001 sends 1999 posts concurrently
- User 6144 sends 1 post
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


class MultiAuthorConsistencyTest:
    def __init__(self, post_service_url: str, timeline_service_url: str, timeline_limit: Optional[int] = None):
        """Initialize with HTTP endpoints"""
        self.post_url = post_service_url
        self.timeline_url = timeline_service_url
        self.timeline_limit = timeline_limit if timeline_limit and timeline_limit > 0 else None
    
    def run_test(
        self,
        authors: List[Tuple[int, int]],  # List of (author_id, num_posts) tuples
        follower_id: int,
        strategy: str,
        output_file: Optional[str] = None,
    ):
        """
        Run the multi-author consistency test
        
        Args:
            authors: List of tuples (author_id, num_posts)
            follower_id: User following the authors (will check their timeline)
            strategy: 'push' or 'pull'
        """
        print(f"\n{'='*60}")
        print(f"Multi-Author Consistency Test - {strategy.upper()} Strategy")
        print(f"{'='*60}")
        print(f"Authors:")
        for author_id, num_posts in authors:
            print(f"  - User {author_id}: {num_posts} posts")
        print(f"Follower: User {follower_id}")
        print()
        
        # Step 1: Create posts from all authors concurrently
        print(f"Step 1: Creating posts from all authors concurrently...")
        all_created_posts = self.create_posts_concurrent(authors)
        
        # Organize results by author
        author_results = {}
        for author_id, num_posts in authors:
            author_posts = [p for p in all_created_posts if p.get('user_id') == author_id]
            author_results[author_id] = {
                'expected': num_posts,
                'created': author_posts,
                'created_count': len(author_posts)
            }
            print(f"✓ User {author_id}: Created {len(author_posts)}/{num_posts} posts")
        
        # Step 2: Wait a moment for async processing (if push strategy)
        if strategy == 'push':
            print(f"\nStep 2: Waiting 2 seconds for async fanout processing...")
            time.sleep(2)
        
        # Step 3: Retrieve follower's timeline
        print(f"\nStep 3: Checking User {follower_id}'s timeline...")
        total_expected = sum(num_posts for _, num_posts in authors)
        retrieved_posts = self.get_timeline_posts(follower_id, [aid for aid, _ in authors], total_expected)
        print(f"✓ Retrieved {len(retrieved_posts)} total posts from timeline")
        
        # Step 4: Calculate inconsistency for each author
        print(f"\nStep 4: Calculating inconsistency for each author...")
        results_by_author = {}
        overall_missing = 0
        overall_created = 0
        
        for author_id, num_posts in authors:
            author_created = author_results[author_id]['created']
            author_retrieved = [p for p in retrieved_posts if (
                p.get('author_id') == author_id or p.get('user_id') == author_id
            )]
            
            missing_posts = self.find_missing_posts(author_created, author_retrieved)
            total_created = len(author_created)
            inconsistency_ratio = (len(missing_posts) / total_created * 100) if total_created else 0.0
            consistency_ratio = 100 - inconsistency_ratio
            
            results_by_author[author_id] = {
                'expected_posts': num_posts,
                'created_posts': total_created,
                'retrieved_posts': len(author_retrieved),
                'missing_posts': len(missing_posts),
                'consistency_ratio': consistency_ratio,
                'inconsistency_ratio': inconsistency_ratio,
                'missing_contents': missing_posts,
            }
            
            overall_created += total_created
            overall_missing += len(missing_posts)
            
            print(f"\n  User {author_id}:")
            print(f"    Created:     {total_created}/{num_posts}")
            print(f"    Retrieved:   {len(author_retrieved)}")
            print(f"    Missing:     {len(missing_posts)}")
            print(f"    Consistency: {consistency_ratio:.2f}%")
        
        # Overall results
        overall_consistency = ((overall_created - overall_missing) / overall_created * 100) if overall_created else 0.0
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"Total posts created:     {overall_created}")
        print(f"Total posts retrieved:   {sum(len([p for p in retrieved_posts if (
            p.get('author_id') == aid or p.get('user_id') == aid
        )]) for aid, _ in authors)}")
        print(f"Total missing posts:     {overall_missing}")
        print(f"Overall consistency:     {overall_consistency:.2f}%")
        print(f"{'='*60}\n")
        
        result = {
            'strategy': strategy,
            'authors': {aid: results_by_author[aid] for aid, _ in authors},
            'follower_id': follower_id,
            'overall': {
                'total_created': overall_created,
                'total_missing': overall_missing,
                'consistency_ratio': overall_consistency,
            },
            'timeline_limit': self.timeline_limit,
        }

        self.save_results(result, output_file)

        return result
    
    def create_posts_concurrent(self, authors: List[Tuple[int, int]]) -> List[Dict]:
        """
        Create posts from multiple authors concurrently
        
        Args:
            authors: List of (author_id, num_posts) tuples
            
        Returns:
            List of created posts with user_id, post_id, and content
        """
        all_results: List[Dict] = []
        start_time = time.time()
        
        def send_post(author_id: int, post_index: int):
            """Send a single post request"""
            payload = {
                "user_id": author_id,
                "content": f"Test post from user {author_id} - #{post_index}",
            }
            try:
                response = requests.post(
                    f"{self.post_url}/api/posts",
                    json=payload,
                    timeout=10
                )
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                post_id = self._extract_post_id(data)
                return {
                    'user_id': author_id,
                    'post_id': post_id,
                    'content': payload['content'],
                    'status': response.status_code,
                    'success': response.status_code == 200 and post_id is not None,
                }
            except requests.RequestException as exc:
                return {
                    'user_id': author_id,
                    'post_id': None,
                    'content': payload['content'],
                    'status': None,
                    'success': False,
                    'error': str(exc),
                }
        
        # Create all tasks
        tasks = []
        for author_id, num_posts in authors:
            for i in range(1, num_posts + 1):
                tasks.append((author_id, i))
        
        # Execute all tasks concurrently
        completed = 0
        total_tasks = len(tasks)
        
        with ThreadPoolExecutor(max_workers=min(200, total_tasks)) as executor:
            futures = {executor.submit(send_post, author_id, post_idx): (author_id, post_idx) 
                      for author_id, post_idx in tasks}
            
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if result['success']:
                    all_results.append({
                        'user_id': result['user_id'],
                        'post_id': result['post_id'],
                        'content': result['content'],
                    })
                
                if completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    print(f"   Progress: {completed}/{total_tasks} ({rate:.1f} posts/sec)")
        
        elapsed = time.time() - start_time
        rate = len(all_results) / elapsed if elapsed > 0 else 0
        print(f"   Total time: {elapsed:.2f} seconds ({rate:.1f} posts/sec)")
        
        return all_results
    
    def get_timeline_posts(
        self, 
        follower_id: int, 
        author_ids: List[int], 
        limit_hint: Optional[int]
    ) -> List[Dict[str, str]]:
        """
        Get follower's timeline via HTTP GET and extract posts from specified authors
        
        Returns list of posts from the authors
        """
        try:
            params = {}
            if self.timeline_limit:
                params["limit"] = self.timeline_limit
            elif limit_hint:
                params["limit"] = min(limit_hint + 100, 20000)  # Add buffer
            else:
                params["limit"] = 20000
            
            response = requests.get(
                f"{self.timeline_url}/api/timeline/{follower_id}",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('posts') or data.get('timeline') or []

                if not posts:
                    preview = json.dumps(data)[:300]
                    print("   ! Timeline returned 0 posts; raw response snippet:")
                    print(f"     {preview}")

                # Filter posts from our authors
                author_posts = [
                    {
                        'post_id': post.get('post_id'),
                        'content': post.get('content'),
                        'user_id': post.get('user_id'),
                        'author_id': post.get('author_id'),
                    }
                    for post in posts
                    if (
                        post.get('author_id') in author_ids
                        or post.get('user_id') in author_ids
                    )
                ]

                if not author_posts:
                    print(f"   ! No posts from authors {author_ids} found in timeline response")

                return author_posts
            else:
                print(f"   ✗ Error getting timeline: Status {response.status_code}")
                print(f"     Response: {response.text[:200]}")
                return []
            
        except requests.RequestException as e:
            print(f"   ✗ Error getting timeline: {e}")
            return []
    
    def find_missing_posts(
        self,
        created: List[Dict[str, str]],
        retrieved: List[Dict[str, str]]
    ) -> List[str]:
        """
        Find missing posts using content as the identifier.
        """
        created_contents = {p['content'] for p in created if p.get('content')}
        retrieved_contents = {p['content'] for p in retrieved if p.get('content')}

        return sorted(created_contents - retrieved_contents)

    @staticmethod
    def _extract_post_id(data: Dict) -> Optional[str]:
        """Handle multiple response shapes from post-service."""
        if not isinstance(data, dict):
            return None
        if 'post_id' in data:
            return data['post_id']
        post_obj = data.get('post')
        if isinstance(post_obj, dict):
            return post_obj.get('post_id')
        return None

    def save_results(self, result: dict, output_file: Optional[str]) -> None:
        """Persist results to disk for later inspection."""
        target = output_file or f"multi_author_result_{result['strategy']}_{int(time.time())}.json"
        try:
            path = Path(target).expanduser().resolve()
            path.write_text(json.dumps(result, indent=2))
            print(f"\nResults written to {path}")
        except OSError as exc:
            print(f"\n✗ Failed to write results to {target}: {exc}")


def main():
    parser = argparse.ArgumentParser(description='Multi-Author Post Consistency Test')
    parser.add_argument('--strategy', type=str, required=True, 
                        choices=['push', 'pull'],
                        help='Fan-out strategy to test')
    parser.add_argument('--follower-id', type=int, default=2001,
                        help='Follower user ID (who views timeline)')
    parser.add_argument('--post-service', type=str, default='http://localhost:8080',
                        help='Post service URL')
    parser.add_argument('--timeline-service', type=str, default='http://localhost:8081',
                        help='Timeline service URL')
    parser.add_argument('--output-file', type=str, default=None,
                        help='Optional path to save JSON results')
    parser.add_argument('--timeline-limit', type=int, default=None,
                        help='Timeline API limit (default: no limit)')
    
    args = parser.parse_args()
    
    # Define authors: User 5001 sends 1999 posts, User 6144 sends 1 post
    authors = [
        (5001, 100),  # User 5001: 1999 posts
        (6144, 300), # User 6144: 1 post
    ]
    
    print(f"\nNote: Make sure the following users have correct follower counts for {args.strategy} strategy:")
    for author_id, _ in authors:
        print(f"  - User {author_id}: Push strategy needs < 10,000 followers, Pull needs >= 10,000")
    print(f"  - User {args.follower_id} should be following all authors: {[aid for aid, _ in authors]}")
    
    # Run test
    tester = MultiAuthorConsistencyTest(
        args.post_service,
        args.timeline_service,
        timeline_limit=args.timeline_limit
    )
    
    result = tester.run_test(
        authors=authors,
        follower_id=args.follower_id,
        strategy=args.strategy,
        output_file=args.output_file,
    )
    
    # Return exit code based on overall consistency
    overall_consistency = result['overall']['consistency_ratio']
    if overall_consistency == 100.0:
        exit(0)  # Success
    else:
        exit(1)  # Some posts missing


if __name__ == '__main__':
    main()

