import csv
import logging
import os
from typing import Dict, List
from prisma import Prisma
from datetime import datetime
import config
import prisma.models  # Import generated models
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Set up logging (will be overridden by main.py's setup_logger)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrismaOperations:
    def __init__(self):
        self.prisma = Prisma(auto_register=True)

    async def connect(self):
        await self.prisma.connect()

    async def disconnect(self):
        await self.prisma.disconnect()

    async def get_max_seq_no(self) -> int:
        """Fetch the largest seqNo from the LARPScript table."""
        scripts = await self.prisma.larpscript.find_many(order={'seqNo': 'desc'}, take=1)
        if scripts and scripts[0].seqNo is not None:
            return scripts[0].seqNo
        return 0

    async def upsert_larp_script(self, row: Dict[str, str], seq_no: int) -> bool:
        """Upsert a LARPScript record based on CSV row data."""
        try:
            script_id = row['scriptId']
            script_name = row['scriptName']
            description = row.get('scriptTextContent', '')
            player_count = int(row.get('scriptPlayerLimit', '0') or '0')
            male_player_count = int(row.get('scriptMalePlayerLimit', '0') or '0')
            female_player_count = int(row.get('scriptFemalePlayerLimit', '0') or '0')
            duration_in_hour = float(row.get('groupDuration', '0') or '0') / 60
            issue_time_str = row.get('scriptIssueUnitTime', '')
            issue_time = datetime.fromtimestamp(int(issue_time_str)) if issue_time_str and issue_time_str.isdigit() else None
            mq_script_id = row['scriptId']
            mq_collective_score = float(row.get('scriptScore', '0') or '0')
            mq_score_count = int(row.get('scriptScoreCount', '0') or '0')
            mq_inference_score = float(row.get('scriptInferenceScore', '0') or '0')
            mq_plot_score = float(row.get('scriptPlotScore', '0') or '0')
            mq_complex_score = float(row.get('scriptComplexScore', '0') or '0')
            mq_want_player_count = int(row.get('scriptWantPlayerCount', '0') or '0')
            mq_script_image_content = row.get('scriptImageContent', '')
            played_count = int(row.get('scriptPlayedCount', '0') or '0')

            script_tags = row.get('scriptTag', '').split('@')
            script_tags = [tag for tag in script_tags if tag and tag != '其他']
            difficulty = row.get('scriptDifficultyDegreeName', '')
            script_category = row.get('scriptCategory', '')

            # Map tags
            tag_booleans = {field: False for field in config.TAG_MAPPING.values()}
            other_tags = []
            for tag in script_tags:
                if tag in config.TAG_MAPPING:
                    tag_booleans[config.TAG_MAPPING[tag]] = True
                else:
                    other_tags.append(tag)

            # Map difficulty
            difficulty_booleans = {field: False for field in config.DIFFICULTY_MAPPING.values()}
            if difficulty in config.DIFFICULTY_MAPPING:
                difficulty_booleans[config.DIFFICULTY_MAPPING[difficulty]] = True

            # Map sold-by
            sold_by_booleans = {field: False for field in config.SOLD_BY_MAPPING.values()}
            if script_category in config.SOLD_BY_MAPPING:
                sold_by_booleans[config.SOLD_BY_MAPPING[script_category]] = True

            # Image URL
            image_url = None
            if row.get('scriptCoverUrl') and mq_script_id:
                file_extension = row['scriptCoverUrl'].split('.').pop()
                image_url = f"{mq_script_id}.{file_extension}"

            update_data = {
                'name': script_name,
                'imageUrl': image_url,
                'description': description,
                'playerCount': player_count,
                'playerMaleCount': male_player_count,
                'playerFemaleCount': female_player_count,
                'durationInHour': duration_in_hour,
                'author': [],
                'publisher': [],
                'otherTags': other_tags,
                **tag_booleans,
                **difficulty_booleans,
                **sold_by_booleans,
                'issueTime': issue_time,
                'mqScriptId': mq_script_id,
                'mqCollectiveScore': mq_collective_score,
                'mqScoreCount': mq_score_count,
                'mqInferenceScore': mq_inference_score,
                'mqPlotScore': mq_plot_score,
                'mqComplexScore': mq_complex_score,
                'mqWantPlayerCount': mq_want_player_count,
                'mqScriptImageContent': mq_script_image_content,
                'playedCount': played_count,
            }

            create_data = {
                **update_data,
                'isPlayerCountFixed': True,
                'isDurationFixed': True,
                'seqNo': seq_no,
            }

            await self.prisma.larpscript.upsert(
                where={'mqScriptId': mq_script_id},
                data={'update': update_data, 'create': create_data}
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting scriptId {script_id}: {e}")
            return False

    async def upsert_issuers_and_authors(self, row: Dict[str, str]):
        """Upsert issuers and authors for a script based on row data."""
        script_id = row['scriptId']
        issue_info_items = row.get('scriptIssueInfoItems', '')

        if not issue_info_items or issue_info_items.strip() == '':
            return

        issue_items = [item.strip() for item in issue_info_items.split(',')]
        script = await self.prisma.larpscript.find_unique(where={'mqScriptId': script_id})
        if not script:
            return

        for item in issue_items:
            try:
                name, id_bracket = item.split(' ', 1) if ' ' in item else (item, 'None')
                unit_id = id_bracket.replace('(', '').replace(')', '')

                if unit_id == 'None':
                    authors = [a.strip() for a in name.split('&')]
                    for author in authors:
                        author_record = await self.prisma.larpscriptauthor.upsert(
                            where={'name': author},
                            data={'create': {'name': author}, 'update': {}}
                        )
                        await self.prisma.larpscriptswrittenbyauthors.upsert(
                            where={'scriptId_authorId': {'scriptId': script.id, 'authorId': author_record.id}},
                            data={'create': {'scriptId': script.id, 'authorId': author_record.id}, 'update': {}}
                        )
                else:
                    issuer_record = await self.prisma.larpscriptissuer.upsert(
                        where={'mqIssueUnitId': unit_id},
                        data={'create': {'mqIssueUnitId': unit_id, 'name': name, 'intro': ''}, 'update': {}}
                    )
                    await self.prisma.larpscriptsissuedbyissuers.upsert(
                        where={'scriptId_issuerId': {'scriptId': script.id, 'issuerId': issuer_record.id}},
                        data={'create': {'scriptId': script.id, 'issuerId': issuer_record.id}, 'update': {}}
                    )
            except Exception as e:
                logger.error(f"Error processing issue item '{item}' for scriptId {script_id}: {e}")

    async def process_script(self, row: Dict[str, str], seq_no: int, index: int, total: int):
        """Process a single script with logging."""
        script_id = row['scriptId']
        script_name = row['scriptName']
        logger.info(f"{index + 1}/{total}: {script_id} {script_name}")
        success = await self.upsert_larp_script(row, seq_no)
        if success:
            await self.upsert_issuers_and_authors(row)
        return success

async def import_scripts_and_relations(new_details: List[Dict[str, str]], max_concurrency: int = 50):
    """Import scripts and their issuers/authors into Prisma database in parallel."""
    prisma_ops = PrismaOperations()
    await prisma_ops.connect()

    total_rows = len(new_details)
    if total_rows == 0:
        logger.info("No scripts to upsert.")
        await prisma_ops.disconnect()
        return

    max_seq_no = await prisma_ops.get_max_seq_no()
    current_seq_no = max_seq_no

    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_task(row, seq_no, index):
        async with semaphore:
            return await prisma_ops.process_script(row, seq_no, index, total_rows)

    # Create tasks for all rows
    tasks = [
        sem_task(row, current_seq_no + i + 1, i)
        for i, row in enumerate(new_details)
    ]

    # Execute tasks in parallel and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    upsert_count = sum(1 for result in results if result is True)
    failed_count = total_rows - upsert_count

    logger.info(f"Success: {upsert_count} rows upserted.")
    logger.info(f"Failed: {failed_count} rows.")

    await prisma_ops.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(import_scripts_and_relations([]))