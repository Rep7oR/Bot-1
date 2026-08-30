import os
import json
import asyncio
from copy import deepcopy


# ============================================================
# CONFIGURATION MANAGER
# ============================================================

class ConfigManager:

    def __init__(self, file_path="data/bot_config.json"):

        self.file_path = file_path
        self.lock = asyncio.Lock()

        os.makedirs(
            os.path.dirname(self.file_path),
            exist_ok=True
        )

        self.data = self._load()

    # ========================================================
    # LOAD
    # ========================================================

    def _load(self):

        if not os.path.exists(self.file_path):

            return {}

        try:

            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if isinstance(data, dict):

                    return data

        except Exception as e:

            print(
                f"❌ Config load error: {e}"
            )

        return {}

    # ========================================================
    # SAVE
    # ========================================================

    def _save(self):

        temp_file = (
            self.file_path + ".tmp"
        )

        try:

            with open(
                temp_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            os.replace(
                temp_file,
                self.file_path
            )

            return True

        except Exception as e:

            print(
                f"❌ Config save error: {e}"
            )

            return False

    # ========================================================
    # GUILD
    # ========================================================

    def get_guild(
        self,
        guild_id
    ):

        guild_id = str(
            guild_id
        )

        if guild_id not in self.data:

            self.data[guild_id] = {}

        return self.data[guild_id]

    # ========================================================
    # COG
    # ========================================================

    def get_cog(
        self,
        guild_id,
        cog_name
    ):

        guild = self.get_guild(
            guild_id
        )

        if cog_name not in guild:

            guild[cog_name] = {}

        return guild[cog_name]

    # ========================================================
    # SET COG CONFIG
    # ========================================================

    async def set_cog(
        self,
        guild_id,
        cog_name,
        config
    ):

        async with self.lock:

            guild_id = str(
                guild_id
            )

            if guild_id not in self.data:

                self.data[guild_id] = {}

            self.data[guild_id][
                cog_name
            ] = deepcopy(config)

            self._save()

    # ========================================================
    # UPDATE COG CONFIG
    # ========================================================

    async def update_cog(
        self,
        guild_id,
        cog_name,
        **values
    ):

        async with self.lock:

            guild_id = str(
                guild_id
            )

            if guild_id not in self.data:

                self.data[guild_id] = {}

            if cog_name not in self.data[guild_id]:

                self.data[guild_id][
                    cog_name
                ] = {}

            self.data[guild_id][
                cog_name
            ].update(
                deepcopy(values)
            )

            self._save()

    # ========================================================
    # GET CONFIG
    # ========================================================

    def get(
        self,
        guild_id,
        cog_name,
        default=None
    ):

        guild_id = str(
            guild_id
        )

        guild = self.data.get(
            guild_id,
            {}
        )

        config = guild.get(
            cog_name,
            default
        )

        if config is None:

            return default

        return deepcopy(
            config
        )

    # ========================================================
    # DELETE
    # ========================================================

    async def delete(
        self,
        guild_id,
        cog_name
    ):

        async with self.lock:

            guild_id = str(
                guild_id
            )

            if guild_id in self.data:

                self.data[
                    guild_id
                ].pop(
                    cog_name,
                    None
                )

                self._save()

    # ========================================================
    # ALL GUILD CONFIG
    # ========================================================

    def get_all(
        self,
        guild_id
    ):

        guild_id = str(
            guild_id
        )

        return deepcopy(
            self.data.get(
                guild_id,
                {}
            )
        )

    # ========================================================
    # CHECK WHETHER CONFIG EXISTS
    # ========================================================

    def exists(
        self,
        guild_id,
        cog_name
    ):

        guild_id = str(
            guild_id
        )

        return (
            guild_id in self.data
            and cog_name in self.data[guild_id]
            and bool(
                self.data[guild_id][
                    cog_name
                ]
            )
        )

    # ========================================================
    # FORCE SAVE
    # ========================================================

    async def save(self):

        async with self.lock:

            self._save()


# ============================================================
# GLOBAL CONFIG INSTANCE
# ============================================================

config_manager = ConfigManager()
