from discord.ext import commands, tasks
import discord
import asyncio
from utils.gsheet import GSheet
from sqlite3 import IntegrityError

class Registration(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.occupied = False
        self.lock = asyncio.Lock()
        self.not_registered = []
        self.participant_data = {}
        self.tokens = []
        self.sheet = GSheet()

        self.bot.loop.create_task(self.updateData())


    async def updateData(self):

        await self.bot.wait_until_ready()

        guild = self.bot.guilds[0]

        async with self.bot.db.execute("SELECT id FROM notregistered") as cursor:
            rows = await cursor.fetchall()

            try:
                self.not_registered = [guild.get_member(int(i[0])) for i in rows if i[0] is not None]

            except IndexError:
                self.not_registered = []


            print("Registration:", self.not_registered)
            self.get_data.start()


    @tasks.loop(minutes=10)
    async def get_data(self):

        # Ensures we only scrape in one thread
        if self.occupied:
            return

        self.occupied = True
        self.participant_data = await asyncio.to_thread(self.sheet.registration_sheet)
        self.tokens = await asyncio.to_thread(self.sheet.retrieve_tokens)
        self.occupied = False
        await self.attempt_registration()

    async def attempt_registration(self):

        not_reg_copy = self.not_registered.copy()

        for i in range(len(not_reg_copy)):

            member = not_reg_copy[i]
            search_str = self.participant_data.get(f"{member.name}#{member.discriminator}")

            if search_str and member.guild:
                found = discord.Embed(
                    title="Registration Update",
                    description="Thank you for registering! We have given you a role to access more channels.",
                    color=discord.Colour.green(),
                    type="rich"
                )

                found.add_field(name="Registered Email", value=search_str, inline=True)
                found.set_footer(
                    text="If you believe the email provided is not yours, please contact an organizer immediately.")

                # Registered Hacker Role
                await member.add_roles(member.guild.get_role(1087192865186254999))

                # Hacker Role
                await member.remove_roles(member.guild.get_role(1085682655326130316))

                # Ensures resource is available before popping
                async with self.lock:
                    try:
                        self.not_registered.remove(member)

                    except Exception as e:
                        print(f"Was unable to remove {member.name} from not_registered list")

                sql = 'DELETE FROM notregistered WHERE id=?'

                async with self.bot.db.execute(sql, (member.id,)) as cursor:
                    await self.bot.db.commit()

                await member.send(embed=found)
                print("Sent message to user")


    @commands.guild_only()
    @commands.is_owner()
    @commands.command(name="purgedenied", description="Causes the purge", aliases=['pd'])
    async def purgedenied(self, ctx):

        reg_role = ctx.guild.get_role(1087192865186254999)
        hacker = ctx.guild.get_role(1085682655326130316)

        for member in ctx.guild.members:
            search_str = self.participant_data.get(f"{member.name}#{member.discriminator}")

            if reg_role in member.roles and not search_str:

                desc = 'We regret to inform you that we are unable to accept your application to participate in DeerHacks at this time. We received a large number of applications, and while we appreciate your interest and effort, we had to make some difficult decisions in the selection process.\n\nWe hope that you understand that this decision was not a reflection of your skills or abilities. We still encourage you to join us during the hackathon, as we will be offering some exceptional workshops that anyone can participate in.\n\nWe appreciate your interest in DeerHacks and hope to see you at future events.\n\nBest regards, The DeerHacks Team.'

                denied = discord.Embed(
                    title=f"Hi {member.name},",
                    description=desc,
                    colour=discord.Colour.blue(),
                    type="rich"
                )

                # Registered Hacker Role
                await member.remove_roles(reg_role)

                # Hacker Role
                await member.add_roles(hacker)

                await member.send(embed=denied)

            elif reg_role in member.roles and search_str:

                accepted = discord.Embed(
                    title="Congratulations!",
                    description="Your application to DeerHacks has been accepted. Keep an eye out for announcements!",
                    color=discord.Colour.gold(),
                    type="rich"
                )

                await member.send(embed=accepted)

        await ctx.send("Command Successful.")



    @commands.command(name="validate", description="Command to validate token", aliases=['v'])
    async def validate(self, ctx, token : str):

        if ctx.author.mutual_guilds and ctx.channel == ctx.author.dm_channel and ctx.author in self.not_registered:
            guild = ctx.author.mutual_guilds[0]
            if token in self.tokens:
                member = guild.get_member(ctx.author.id)
                await member.add_roles(guild.get_role(1087192865186254999))
                await member.remove_roles(guild.get_role(1085682655326130316))

                async with self.lock:
                    self.not_registered.remove(ctx.author)

                sql = 'DELETE FROM notregistered WHERE id=?'

                async with self.bot.db.execute(sql, (ctx.author.id,)) as cursor:
                    await self.bot.db.commit()

                found = discord.Embed(
                    title="Successfully Validated",
                    description="Thank you for registering! We have given you a role to access more channels.",
                    color=discord.Colour.green(),
                    type="rich"
                )

                await ctx.author.send(embed=found)
                return

        desc = """This could be for many reasons:
        
        • You already have the 'Registered Hacker' role
        • You did not use the command in our dms
        • You are not in the DeerHacks Server
        
        If none of these apply to you, please try again in 15 minutes. Contact an organizer if this issue persists.
        
        """
        not_found = discord.Embed(
            title="Your request was unable to be completed",
            description=desc,
            color=discord.Colour.red(),
            type="rich"
        )

        await ctx.author.send(embed=not_found)



    @commands.Cog.listener('on_member_remove')
    async def on_member_remove_reg(self, member):

        if member in self.not_registered:
            async with self.lock:
                self.not_registered.remove(member)

            sql = 'DELETE FROM notregistered WHERE id=?'

            async with self.bot.db.execute(sql, (member.id,)) as cursor:
                await self.bot.db.commit()



    @commands.Cog.listener()
    async def on_member_join(self, member):

        search_str = self.participant_data.get(f"{member.name}#{member.discriminator}")

        if search_str:

            found = discord.Embed(
                title="Welcome to DeerHacks 2023!",
                description="Thank you for registering! We have given you a role to access more channels.",
                color=discord.Colour.green(),
                type="rich"
            )

            found.add_field(name="Registered Email", value=search_str, inline=True)
            found.set_footer(text="If you believe the email provided is not yours, please contact an organizer immediately.")

            await member.send(embed=found)

            # Registered Hacker Role
            await member.add_roles(member.guild.get_role(1087192865186254999))

        else:

            desc = """Please register via https://register.deerhacks.ca to get verified.
            
            • If you are unable to register using the link above, the registration period may be over. Please contact an organizer for more information.
            
            • If you have registered and provided your discord username during registration, but still see this message, please wait at least 15 minutes to receive 
            your role. Contact an organizer if you do not receive your role after 15 minutes.
            
            • If you have registered, but did not enter your discord username during registration, please provide me the QR code you recieved through your email.
            Note that QR codes are only given after the acceptance period is finished. If this period has not finished, please wait until it has.
            
            Command usage: dh.validate <QR Code Link>
            Example: dh.validate https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=example
            """

            not_found = discord.Embed(
                title="Welcome to DeerHacks 2023!",
                description=desc,
                colour=discord.Colour.red(),
                type="rich"
            )

            not_found.set_footer(text="Please contact an organizer immediately for any questions or concerns.")

            # Hacker Role
            await member.add_roles(member.guild.get_role(1085682655326130316))

            async with self.lock:
                self.not_registered.append(member)

            await member.send(embed=not_found)

            sql = 'INSERT INTO notregistered(id) VALUES (?)'

            try:
                async with self.bot.db.execute(sql, (member.id,)) as cursor:
                    await self.bot.db.commit()

            except IntegrityError:
                return


async def setup(bot):
    await bot.add_cog(Registration(bot))
