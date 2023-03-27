from discord.ext import commands, tasks
import discord
import asyncio
from utils.gsheet import GSheet
from sqlite3 import IntegrityError


class InPerson(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.occupied = False
        self.lock = asyncio.Lock()
        self.do_not_send = []
        self.attendees = []
        self.sheet = GSheet()

        self.bot.loop.create_task(self.updateData())


    async def updateData(self):

        await self.bot.wait_until_ready()

        guild = self.bot.guilds[0]

        async with self.bot.db.execute("SELECT id FROM dontmsg") as cursor:
            rows = await cursor.fetchall()

            try:
                self.do_not_send = [guild.get_member(int(i[0])) for i in rows if i[0] is not None]

            except IndexError:
                self.do_not_send = []


            print("In Person:", self.do_not_send)
            self.get_data.start()


    @tasks.loop(minutes=15)
    async def get_data(self):

        # Ensures we only scrape in one thread
        if self.occupied:
            return

        self.occupied = True
        self.attendees = await asyncio.to_thread(self.sheet.inperson_sheet)
        self.occupied = False

        await self.attempt_delegation()

    async def attempt_delegation(self):

        await self.bot.wait_until_ready()
        guild = self.bot.guilds[0]

        for member in guild.members:
            member_name = f"{member.name}#{member.discriminator}"

            if member_name in self.attendees and member not in self.do_not_send:

                # Registered Hacker Role
                await member.remove_roles(member.guild.get_role(1087192865186254999))

                # Verified Hacker Role
                await member.add_roles(member.guild.get_role(1087193230157819925))

                embed = discord.Embed(
                    title="Awesome to see you here!",
                    description="Your presence just made our party a lot cooler. And hey, I've just granted you VIP access to all the juicy stuff, so get ready to have a blast!",
                    color=discord.Colour.purple(),
                    type="rich"
                )

                await member.send(embed=embed)

                async with self.lock:
                    self.do_not_send.append(member)

                sql = 'INSERT INTO dontmsg(id) VALUES (?)'

                try:
                    async with self.bot.db.execute(sql, (member.id,)) as cursor:
                        await self.bot.db.commit()

                except IntegrityError:
                    return


    @commands.Cog.listener('on_member_remove')
    async def on_member_remove_in(self, member):

        if member in self.do_not_send:
            async with self.lock:
                self.do_not_send.remove(member)

            sql = 'DELETE FROM dontmsg WHERE id=?'

            async with self.bot.db.execute(sql, (member.id,)) as cursor:
                await self.bot.db.commit()



async def setup(bot):
    await bot.add_cog(InPerson(bot))