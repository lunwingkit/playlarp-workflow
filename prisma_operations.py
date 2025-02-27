# prisma_operations.py

import csv
import logging
import os
from typing import Dict, List
from prisma import Prisma
from datetime import datetime
import config
import prisma.models  # Import generated models

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrismaOperations:
    def __init__(self):
        self.prisma = Prisma(auto_register=True)  # Auto-register models from prisma.models

    async def connect(self):
        await self.prisma.connect()

    async def disconnect(self):
        await self.prisma.disconnect()

    async def get_max_seq_no(self) -> int:
        """Fetch the largest seqNo from the LARPScript table."""
        # Fetch all scripts with seqNo, order by seqNo descending, take the first one
        scripts = await self.prisma.larpscript.find_many(
            order={'seqNo': 'desc'},
            take=1
        )
        if scripts and scripts[0].seqNo is not None:
            return scripts[0].seqNo
        return 0  # Return 0 if no scripts or seqNo is None

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
            issue_time = datetime.fromtimestamp(int(issue_time_str)) if issue_time_str else None
            mq_script_id = row['scriptId']
            mq_collective_score = float(row.get('scriptScore', '0') or '0')
            mq_score_count = int(row.get('scriptScoreCount', '0') or '0')
            mq_inference_score = float(row.get('scriptInferenceScore', '0') or '0')
            mq_plot_score = float(row.get('scriptPlotScore', '0') or '0')
            mq_complex_score = float(row.get('scriptComplexScore', '0') or '0')
            mq_want_player_count = int(row.get('scriptWantPlayerCount', '0') or '0')
            mq_script_image_content = row.get('scriptImageContent', '')
            played_count = int(row.get('scriptPlayedCount', '0') or '0')

            # Tags and difficulty
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

            # Prepare data for upsert
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

            # Upsert LARPScript
            script = await self.prisma.larpscript.upsert(
                where={'mqScriptId': mq_script_id},
                data={
                    'update': update_data,
                    'create': create_data
                }
            )
            logger.info(f"Script upserted successfully for scriptId: {script_id}")
            return True
        except Exception as e:
            logger.error(f"Error upserting scriptId {script_id}: {e}")
            return False

    async def upsert_issuers_and_authors(self, row: Dict[str, str]):
        """Upsert issuers and authors for a script based on row data."""
        script_id = row['scriptId']
        issue_info_items = row.get('scriptIssueInfoItems', '')

        if not issue_info_items or issue_info_items.strip() == '':
            logger.info(f"No issue or author info for scriptId: {script_id}")
            return

        issue_items = [item.strip() for item in issue_info_items.split(',')]
        script = await self.prisma.larpscript.find_unique(where={'mqScriptId': script_id})
        if not script:
            logger.error(f"Script not found for scriptId: {script_id}")
            return

        for item in issue_items:
            try:
                name, id_bracket = item.split(' ', 1) if ' ' in item else (item, 'None')
                unit_id = id_bracket.replace('(', '').replace(')', '')

                if unit_id == 'None':
                    # Handle authors
                    authors = [a.strip() for a in name.split('&')]
                    for author in authors:
                        author_record = await self.prisma.larpscriptauthor.upsert(
                            where={'name': author},
                            data={'create': {'name': author}, 'update': {}}
                        )
                        logger.info(f"Upserted author: {author}")
                        await self.prisma.larpscriptswrittenbyauthors.upsert(
                            where={'scriptId_authorId': {'scriptId': script.id, 'authorId': author_record.id}},
                            data={'create': {'scriptId': script.id, 'authorId': author_record.id}, 'update': {}}
                        )
                        logger.info(f"Linked author {author} to scriptId: {script_id}")
                else:
                    # Handle issuer
                    issuer_record = await self.prisma.larpscriptissuer.upsert(
                        where={'mqIssueUnitId': unit_id},
                        data={
                            'create': {'mqIssueUnitId': unit_id, 'name': name, 'intro': ''},
                            'update': {}
                        }
                    )
                    logger.info(f"Upserted issuer: {name} with id: {unit_id}")
                    await self.prisma.larpscriptsissuedbyissuers.upsert(
                        where={'scriptId_issuerId': {'scriptId': script.id, 'issuerId': issuer_record.id}},
                        data={'create': {'scriptId': script.id, 'issuerId': issuer_record.id}, 'update': {}}
                    )
                    logger.info(f"Linked issuer {name} (ID: {unit_id}) to scriptId: {script_id}")
            except Exception as e:
                logger.error(f"Error processing issue item '{item}' for scriptId {script_id}: {e}")

async def import_scripts_and_relations(new_details: List[Dict[str, str]]):
    """Import only new scripts and their issuers/authors into Prisma database."""
    prisma_ops = PrismaOperations()
    await prisma_ops.connect()

    total_rows = len(new_details)
    upsert_count = 0
    failed_count = 0
    failed_scripts = []

    # Get max seqNo
    max_seq_no = await prisma_ops.get_max_seq_no()
    current_seq_no = max_seq_no

    for index, row in enumerate(new_details):
        logger.info(f"Processing {index + 1}/{total_rows}: scriptId {row['scriptId']}")
        current_seq_no += 1
        success = await prisma_ops.upsert_larp_script(row, current_seq_no)
        if success:
            upsert_count += 1
            await prisma_ops.upsert_issuers_and_authors(row)
        else:
            failed_count += 1
            failed_scripts.append({'scriptId': row['scriptId'], 'scriptName': row['scriptName']})

    logger.info(f"Success: {upsert_count} rows upserted.")
    logger.info(f"Failed: {failed_count} rows.")
    if failed_scripts:
        logger.info("Failed scripts:")
        for script in failed_scripts:
            logger.info(f"scriptId: {script['scriptId']}, scriptName: {script['scriptName']}")

    await prisma_ops.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(import_scripts_and_relations([]))