from discord.ext import commands
import aiosqlite


class Startup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):

        self.bot.db = await aiosqlite.connect('bot.db')

        do_not_msg = '''CREATE TABLE IF NOT EXISTS dontmsg (
        
            id INTEGER UNIQUE
        )
        '''

        not_registered = '''CREATE TABLE IF NOT EXISTS notregistered (
            
            id INTEGER UNIQUE
            
        )
        '''

        await self.bot.db.execute(do_not_msg)
        await self.bot.db.execute(not_registered)
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user.name} | {self.bot.user.id}')



async def setup(bot):
    await bot.add_cog(Startup(bot))
