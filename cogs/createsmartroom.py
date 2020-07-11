import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio
from PIL import Image, ImageFont, ImageDraw
import os
from cogs.slothcurrency import SlothCurrency
from mysqldb import the_data_base
from mysqldb2 import the_data_base5

class CreateSmartRoom(commands.Cog):
	'''
	A cog related to the creation of a custom voice channel.
	'''

	def __init__(self, client):
		self.client = client
		self.vc_id = 693180716258689074
		self.cat_id = 693180588919750778

	@commands.Cog.listener()
	async def on_ready(self):
		print("CreateSmartRoom cog is online")
		self.check_galaxy_expiration.start()


	@tasks.loop(hours=3)
	async def check_galaxy_expiration(self):
		if not await self.table_galaxy_vc_exists():
			return

		epoch = datetime.utcfromtimestamp(0)
		the_time = (datetime.utcnow() - epoch).total_seconds()
		all_rooms = await self.get_all_galaxy_rooms(the_time)
		for room in all_rooms:
			for i in range(2, 6):
				# id, cat, vc, txt1, txt2, txt3, ts
				channel = self.client.get_channel(room[i])
				try:
					await channel.delete()
				except Exception:
					pass

			member = self.client.get_user(room[0])
			category = discord.utils.get(channel.guild.categories, id=room[1])
			try:
				await category.delete()
			except Exception:
				pass

			await member.send(f"**Hey! Your rooms expired so they got deleted!**")


	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		# Checks if the user is leaving the vc and whether there still are people in there
		if before.channel:
			if before.channel.category:
				if before.channel.category.id == self.cat_id:
					user_voice_channel = discord.utils.get(member.guild.channels, id=before.channel.id)
					len_users = len(user_voice_channel.members)
					if len_users == 0 and user_voice_channel.id != self.vc_id:
						txt_channel = await self.get_premium_vc(member.id, user_voice_channel.id)
						if txt_channel:
							the_txt = discord.utils.get(member.guild.channels, id=txt_channel[0][2])
							await the_txt.delete()
						await user_voice_channel.delete()

		# Checks if the user is joining the create a room VC
		if not after.channel:
			return

		if after.channel.id == self.vc_id:
			epoch = datetime.utcfromtimestamp(0)
			the_time = (datetime.utcnow() - epoch).total_seconds()
			old_time = await self.get_user_vc_timestamp(member.id, the_time)
			if not the_time - old_time >= 60:
				await member.send(
					f"**You're on a cooldown, try again in {round(60 - (the_time - old_time))} seconds!**",
					delete_after=5)
				# return await member.move_to(None)
				return
			if the_time - old_time >= 60:
				await self.update_user_vc_ts(member.id, the_time)


			df_msg = await member.send(file=discord.File('./images/smart_vc/selection_menu.png'))
			await df_msg.add_reaction('1️⃣')
			await df_msg.add_reaction('2️⃣')
			await df_msg.add_reaction('3️⃣')

			def check(reaction, user):
				return user == member and str(reaction.emoji) in '1️⃣2️⃣3️⃣'

			# Gets the room type
			reaction, user = await self.get_reaction_response(member, check)
			if reaction is None:
				return

			# Redirects the member to their equivalent room type choice
			if str(reaction.emoji) == '1️⃣':
				await self.basic_room(member)
			elif str(reaction.emoji) == '2️⃣':
				await self.premium_room(member)
			else:
				await self.galaxy_room(member)


	# Room type 1
	async def basic_room(self, member):

		# Checks
		def check_size(m):
			value = m.content
			author = m.author
			if value.isnumeric() and author == member and m.channel == bot_msg.channel:
				value = int(value)
				if value >= 0 and value <= 10:
					return True
				else:
					self.client.loop.create_task(member.send(file=discord.File('./images/smart_vc/basic/1 incorrect.png')))
			elif not value.isnumeric() and author == member and m.channel == bot_msg.channel:
				self.client.loop.create_task(member.send('**Inform a valid value!**'))

		def check_name(m):
			value = m.content
			author = m.author
			if author == member and m.channel == bot_msg.channel:
				if 0 < len(m.content) <= 20:
					return True
				else:
					self.client.loop.create_task(member.send('**Please inform a name having between 1-20 characters!**'))

		def check_confirm(reaction, user):
			return user == member and str(reaction.emoji) in '✅❌'

		# Setting room configs

		# Get the size of the room
		bot_msg = ''
		msg1 = await member.send(file=discord.File('./images/smart_vc/basic/1 select size.png'))
		bot_msg = msg1
		limit = await self.get_response(member, check_size)

		if limit is None:
			return

		# Get the name of the room
		msg2 = await member.send(file=discord.File('./images/smart_vc/basic/1 select name.png'))
		bot_msg = msg2
		name = await self.get_response(member, check_name)

		if name is None:
			return

		# Gets the configuration confirmation
		await self.make_preview_basic(member.id, name, limit)
		msg3 = await member.send(file=discord.File(f'./images/smart_vc/user_previews/{member.id}.png'))
		await msg3.add_reaction('✅')
		await msg3.add_reaction('❌')
		bot_msg = msg3
		reaction, user = await self.get_reaction_response(member, check_confirm)
		if reaction is None:
			return

		# Confirm configurations
		if str(reaction.emoji) == '✅':
			# Gets the CreateSmartRoom category, creates the VC and tries to move the user to there
			the_category_test = discord.utils.get(member.guild.categories, id=self.cat_id)
			creation = await the_category_test.create_voice_channel(name=f"{name}", user_limit=limit)
			await member.send(file=discord.File('./images/smart_vc/created.png'))
			try:
				await member.move_to(creation)
			except discord.errors.HTTPException:
				await member.send("**You cannot be moved because you are not in a Voice-Channel!**")
				await creation.delete()
			finally:
				try:
					os.remove(f'./images/smart_vc/user_previews/{member.id}.png')
				except Exception:
					pass

		# Restart room setup
		else:
			return await self.basic_room(member)

	# Room type 2
	async def premium_room(self, member):
		'''
		To-do:
		- Link the the text channel and the voice channel to the user in the database.
		- Make control commands within the text channel
		'''
		# Checks
		def check_size(m):
			value = m.content
			author = m.author
			if value.isnumeric() and author == member and m.channel == bot_msg.channel:
				value = int(value)
				if value >= 0 and value <= 25:
					return True
				else:
					self.client.loop.create_task(member.send(file=discord.File('./images/smart_vc/premium/incorrect.png')))
			elif not value.isnumeric() and author == member and m.channel == bot_msg.channel:
				self.client.loop.create_task(member.send('**Inform a valid value!**'))

		def check_name(m):
			value = m.content
			author = m.author
			if author == member and m.channel == bot_msg.channel:
				if 0 < len(m.content) <= 20:
					return True
				else:
					self.client.loop.create_task(member.send('**Please inform a name having between 1-20 characters!**'))

		def check_confirm(reaction, user):
			return user == member and str(reaction.emoji) in '✅❌'

		# Setting room configs

		# Get the size of the room
		bot_msg = ''
		msg1 = await member.send(file=discord.File('./images/smart_vc/premium/2 select size.png'))
		bot_msg = msg1
		limit = await self.get_response(member, check_size)

		if limit is None:
			return

		# Get the name of the room
		msg2 = await member.send(file=discord.File('./images/smart_vc/premium/2 select name.png'))
		bot_msg = msg2
		name = await self.get_response(member, check_name)

		if name is None:
			return

		# Gets the configuration confirmation
		await self.make_preview_premium(member.id, name, name, limit)
		msg3 = await member.send(file=discord.File(f'./images/smart_vc/user_previews/{member.id}.png'))
		await msg3.add_reaction('✅')
		await msg3.add_reaction('❌')
		bot_msg = msg3
		reaction, user = await self.get_reaction_response(member, check_confirm)
		if reaction is None:
			return

		# Confirm configurations
		if str(reaction.emoji) == '✅':
			# Checks if the user has money for it (100łł)
			user_currency = await SlothCurrency.get_user_currency(member, member.id)
			if user_currency:
				if user_currency[0][1] >= 100:
					await SlothCurrency.update_user_money(member, member.id, -100)
				else:
					return await member.send("**You don't have enough money to buy this service!**")

			else:
				return await member.send("**You don't even have an account yet!**")
			# Gets the CreateSmartRoom category, creates the VC and text channel and tries to move the user to there
			the_category_test = discord.utils.get(member.guild.categories, id=self.cat_id)
			creation = await the_category_test.create_voice_channel(name=f"{name}", user_limit=limit)
			txt_creation = await the_category_test.create_text_channel(name=f"{name}")
			# Puts the channels ids in the database
			await self.insert_premium_vc(member.id, creation.id, txt_creation.id)
			await member.send(file=discord.File('./images/smart_vc/created.png'))
			try:
				await member.move_to(creation)
			except discord.errors.HTTPException:
				await member.send("**You cannot be moved because you are not in a Voice-Channel! You have one minute to join the room before it gets deleted together with the text channel.**")
				await asyncio.sleep(60)
				if len(creation.members) == 0:
					await creation.delete()
					await txt_creation.delete()
			finally:
				try:
					os.remove(f'./images/smart_vc/user_previews/{member.id}.png')
				except Exception:
					pass


		# Restart room setup
		else:
			return await self.premium_room(member)

	# Room type 3
	async def galaxy_room(self, member):
		'''
		To-do:
		- Link the the text channels and the voice channel to the user in the database.
		- Make control commands within the text channel
		'''

		def check_size(m):
			value = m.content
			author = m.author
			if value.isnumeric() and author == member and m.channel == bot_msg.channel:
				value = int(value)
				if value >= 0 and value <= 25:
					return True
				else:
					self.client.loop.create_task(member.send('**Please, a number between 1 and 25!**'))
			elif not value.isnumeric() and author == member and m.channel == bot_msg.channel:
				self.client.loop.create_task(member.send('**Inform a valid value!**'))

		def check_name(m):
			value = m.content
			author = m.author
			if author == member and m.channel == bot_msg.channel:
				if 0 < len(m.content) <= 20:
					return True
				else:
					self.client.loop.create_task(member.send(file=discord.File('./images/smart_vc/galaxy/3 incorrect vc name.png')))

		def check_cat_or_txt_name(m):
			value = m.content
			author = m.author
			if author == member and m.channel == bot_msg.channel:
				if 0 < len(m.content) <= 10:
					return True
				else:
					self.client.loop.create_task(member.send(file=discord.File('./images/smart_vc/galaxy/3 incorrect text chat name or category.png')))

		def check_confirm(reaction, user):
			return user == member and str(reaction.emoji) in '✅❌'

		# Setting room configs

		# Gets the name of the category
		bot_msg = ''
		msg = await member.send(file=discord.File('./images/smart_vc/galaxy/3 category.png'))
		bot_msg = msg
		category_name = await self.get_response(member, check_cat_or_txt_name)

		if category_name is None:
			return


		# Gets the size of the room
		msg2 = await member.send(file=discord.File('./images/smart_vc/galaxy/3 select size vc.png'))
		bot_msg = msg2
		limit = await self.get_response(member, check_size)

		if limit is None:
			return

		# Gets the name of the room
		msg3 = await member.send(file=discord.File('./images/smart_vc/galaxy/3 select name vc.png'))
		bot_msg = msg3
		vc_name = await self.get_response(member, check_name)

		if vc_name is None:
			return

		# Gets the name of the text channel 1
		msg4 = await member.send(file=discord.File('./images/smart_vc/galaxy/3 select text chat 1.png'))
		bot_msg = msg4
		txt1_name = await self.get_response(member, check_cat_or_txt_name)

		if txt1_name is None:
			return

		# Gets the name of the text channel 2
		msg5 = await member.send(file=discord.File('./images/smart_vc/galaxy/3 select text chat 2.png'))
		bot_msg = msg5
		txt2_name = await self.get_response(member, check_cat_or_txt_name)

		if txt2_name is None:
			return

		# Gets the name of the text channel 3
		msg6 = await member.send(file=discord.File('./images/smart_vc/galaxy/3 select text chat 3.png'))
		bot_msg = msg6
		txt3_name = await self.get_response(member, check_cat_or_txt_name)

		if txt3_name is None:
			return

		# Makes the preview image
		#member_id, cat_name, txt1, txt2, txt3, vc, size
		await self.make_preview_galaxy(member.id, category_name, txt1_name, txt2_name, txt3_name, vc_name, limit)
		# Gets the configuration confirmation
		msg7 = await member.send(file=discord.File(f'./images/smart_vc/user_previews/{member.id}.png'))
		await msg7.add_reaction('✅')
		await msg7.add_reaction('❌')
		bot_msg = msg7
		reaction, user = await self.get_reaction_response(member, check_confirm)
		if reaction is None:
			return

		# Confirm configurations
		if str(reaction.emoji) == '✅':
			# Checks if the user has money (350łł)
			user_currency = await SlothCurrency.get_user_currency(member, member.id)
			if user_currency:
				if user_currency[0][1] >= 350:
					await SlothCurrency.update_user_money(member, member.id, -350)
				else:
					return await member.send("**You don't have enough money to buy this service!**")

			else:
				return await member.send("**You don't even have an account yet!**")
			# Gets the CreateSmartRoom category, creates the VC and text channel and tries to move the user to there
			overwrites = {
			member.guild.default_role: discord.PermissionOverwrite(
				read_messages=False, send_messages=False, connect=False, speak=False, view_channel=False),
			member: discord.PermissionOverwrite(
				read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)
			}
			#, overwrites=overwrites
			category_created = await member.guild.create_category(name=category_name, overwrites=overwrites)
			vc_creation = await category_created.create_voice_channel(name=f"{vc_name}", user_limit=limit)
			txt_creation1 = await category_created.create_text_channel(name=f"{txt1_name}")
			txt_creation2 = await category_created.create_text_channel(name=f"{txt2_name}")
			txt_creation3 = await category_created.create_text_channel(name=f"{txt3_name}")
			# Inserts the channels in the database
			epoch = datetime.utcfromtimestamp(0)
			the_time = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_galaxy_vc(member.id, category_created.id, vc_creation.id, txt_creation1.id, txt_creation2.id, txt_creation3.id, the_time)
			await member.send(file=discord.File('./images/smart_vc/created.png'))
			try:
				await member.move_to(vc_creation)
			except discord.errors.HTTPException:
				await member.send("**You cannot be moved because you are not in a Voice-Channel, but your channels and category will remain alive nonetheless! 👍**")
			finally:
				try:
					os.remove(f'./images/smart_vc/user_previews/{member.id}.png')
				except Exception:
					pass

		else:
			await self.galaxy_room(member)

	async def get_response(self, member, check):
		try:
			response = await self.client.wait_for('message', timeout=60.0, check=check)
			response = response.content
		except asyncio.TimeoutError:
			await member.send(file=discord.File('./images/smart_vc/timeout.png'))
			return None
		else:
			return response

	async def get_reaction_response(self, member, check):
		try:
			reaction, user = await self.client.wait_for('reaction_add', timeout=60.0, check=check)
		except asyncio.TimeoutError:
			timeout = discord.Embed(title='Timeout',
									description='You took too long to answer the questions, try again later.',
									colour=discord.Colour.dark_red())
			await member.send(file=discord.File('./images/smart_vc/timeout.png'))
			return None, None
		else:
			return reaction, user


	async def overwrite_image(self, member_id, text, coords, color, image):
		small = ImageFont.truetype("./images/smart_vc/uni-sans-regular.ttf", 40)
		base = Image.open(image)
		draw = ImageDraw.Draw(base)
		draw.text(coords, text, color, font=small)
		base.save(f'./images/smart_vc/user_previews/{member_id}.png')

	async def overwrite_image_with_image(self, member_id, coords, size):
		f'./images/smart_vc/user_previews/{member_id}.png'
		user_preview = Image.open(f"./images/smart_vc/user_previews/{member_id}.png")
		size_image = Image.open(size).resize((78, 44), Image.LANCZOS)
		user_preview.paste(size_image, coords, size_image)
		user_preview.save(f"./images/smart_vc/user_previews/{member_id}.png")

	async def make_preview_basic(self, member_id, vc, size):
		preview_template = './images/smart_vc/basic/1 preview2.png'
		color = (132, 142, 142)
		await self.overwrite_image(member_id, vc, (585, 870), color, preview_template)
		if int(size) != 0:
			await self.overwrite_image_with_image(member_id, (405, 870), f'./images/smart_vc/sizes/voice channel ({size}).png')

	async def make_preview_premium(self, member_id, txt, vc, size):
		preview_template = './images/smart_vc/premium/2 preview2.png'
		color = (132, 142, 142)
		await self.overwrite_image(member_id, txt.lower(), (585, 760), color, preview_template)
		await self.overwrite_image(member_id, vc, (585, 955), color, f'./images/smart_vc/user_previews/{member_id}.png')
		if int(size) != 0:
			await self.overwrite_image_with_image(member_id, (405, 955), f'./images/smart_vc/sizes/voice channel ({size}).png')

	async def make_preview_galaxy(self, member_id, cat_name, txt1, txt2, txt3, vc, size):
		preview_template = './images/smart_vc/galaxy/3 preview2.png'
		color = (132, 142, 142)
		await self.overwrite_image(member_id, cat_name, (545, 670), color, preview_template)
		await self.overwrite_image(member_id, txt1.lower(), (585, 745), color, f'./images/smart_vc/user_previews/{member_id}.png')
		await self.overwrite_image(member_id, txt2.lower(), (585, 835), color, f'./images/smart_vc/user_previews/{member_id}.png')
		await self.overwrite_image(member_id, txt3.lower(), (585, 930), color, f'./images/smart_vc/user_previews/{member_id}.png')
		await self.overwrite_image(member_id, vc, (585, 1020), color, f'./images/smart_vc/user_previews/{member_id}.png')
		if int(size) != 0:
			await self.overwrite_image_with_image(member_id, (405, 1015), f'./images/smart_vc/sizes/voice channel ({size}).png')


	# Database commands

	# Premium related functions
	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_premium_vc(self, ctx):
		'''
		(ADM) Creates the PremiumVc table.
		'''
		if await self.table_premium_vc_exists():
			return await ctx.send("**Table __PremiumVc__ already exists!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("CREATE TABLE PremiumVc (user_id BIGINT, user_vc BIGINT, user_txt BIGINT)")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __PremiumVc__ created!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_premium_vc(self, ctx):
		'''
		(ADM) Drops the PremiumVc table.
		'''
		if not await self.table_premium_vc_exists():
			return await ctx.send("**Table __PremiumVc__ doesn't exist!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("DROP TABLE PremiumVc")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __PremiumVc__ dropped!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_premium_vc(self, ctx):
		'''
		(ADM) Resets the PremiumVc table.
		'''
		if not await self.table_premium_vc_exists():
			return await ctx.send("**Table __PremiumVc__ doesn't exist yet!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("DELETE FROM PremiumVc")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __PremiumVc__ reset!**")

	async def table_premium_vc_exists(self):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SHOW TABLE STATUS LIKE 'PremiumVc'")
		table_info = await mycursor.fetchall()
		await mycursor.close()
		if len(table_info) == 0:
			return False

		else:
			return True

	async def insert_premium_vc(self, user_id: int, user_vc: int, user_txt: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute("INSERT INTO PremiumVc (user_id, user_vc, user_txt) VALUES (%s, %s, %s)", (user_id, user_vc, user_txt))
		await db.commit()
		await mycursor.close()

	async def get_premium_vc(self, user_id: int, user_vc: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SELECT * FROM PremiumVc WHERE user_id = {user_id} and user_vc = {user_vc}")
		premium_vc = await mycursor.fetchall()
		await mycursor.close()
		return premium_vc

	async def delete_premium_vc(self, user_id: int, user_vc: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"DELETE FROM PremiumVc WHERE user_id = {user_id} and user_vc = {user_vc}")
		await db.commit()
		await mycursor.close()

	# Galaxy related functions
	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_galaxy_vc(self, ctx):
		'''
		(ADM) Creates the GalaxyVc table.
		'''
		if await self.table_galaxy_vc_exists():
			return await ctx.send("**Table __GalaxyVc__ already exists!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("CREATE TABLE GalaxyVc (user_id BIGINT, user_cat BIGINT, user_vc BIGINT, user_txt1 BIGINT, user_txt2 BIGINT, user_txt3 BIGINT, user_ts BIGINT)")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __GalaxyVc__ created!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_galaxy_vc(self, ctx):
		'''
		(ADM) Drops the GalaxyVc table.
		'''
		if not await self.table_galaxy_vc_exists():
			return await ctx.send("**Table __GalaxyVc__ doesn't exist!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("DROP TABLE GalaxyVc")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __GalaxyVc__ dropped!**")

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def reset_table_galaxy_vc(self, ctx):
		'''
		(ADM) Resets the GalaxyVc table.
		'''
		if not await self.table_galaxy_vc_exists():
			return await ctx.send("**Table __GalaxyVc__ doesn't exist yet!**")

		mycursor, db = await the_data_base5()
		await mycursor.execute("DELETE FROM GalaxyVc")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __GalaxyVc__ reset!**")

	async def table_galaxy_vc_exists(self):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SHOW TABLE STATUS LIKE 'GalaxyVc'")
		table_info = await mycursor.fetchall()
		await mycursor.close()
		if len(table_info) == 0:
			return False

		else:
			return True

	async def insert_galaxy_vc(self, user_id: int, user_cat: int, user_vc: int, user_txt1: int, user_txt2: int, user_txt3: int, user_ts: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute("INSERT INTO GalaxyVc (user_id, user_cat, user_vc, user_txt1, user_txt2, user_txt3, user_ts) VALUES (%s, %s, %s, %s, %s, %s, %s)", (user_id, user_cat, user_vc, user_txt1, user_txt2, user_txt3, user_ts))
		await db.commit()
		await mycursor.close()

	async def get_galaxy_txt(self, user_id: int, user_cat: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SELECT * FROM GalaxyVc WHERE user_id = {user_id} and user_cat = {user_cat}")
		premium_vc = await mycursor.fetchall()
		await mycursor.close()
		return premium_vc

	async def get_all_galaxy_rooms(self, the_time: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SELECT * FROM GalaxyVc WHERE {the_time} - user_ts >= 1209600")
		rooms = await mycursor.fetchall()
		await mycursor.close()
		return rooms

	async def delete_galaxy_vc(self, user_id: int, user_vc: int):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"DELETE FROM GalaxyVc WHERE user_id = {user_id} and user_vc = {user_vc}")
		await db.commit()
		await mycursor.close()

	@commands.command(aliases=['permit'])
	async def allow(self, ctx, member: discord.Member = None):
		'''
		Allows a member to join your channels.
		:param member: The member to allow.
		'''
		if not member:
			return await ctx.send("**Inform a member to allow!**")

		user_galaxy = await self.get_galaxy_txt(ctx.author.id, ctx.channel.category.id)
		if user_galaxy:
			user_category = discord.utils.get(ctx.guild.categories, id=user_galaxy[0][1])
			for room in user_galaxy:
				for i in range(2, 6):
					# id, cat, vc, txt1, txt2, txt3, ts
					channel = self.client.get_channel(room[i])
					try:
						await channel.set_permissions(
				member, read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)
					except Exception:
						pass
			await user_category.set_permissions(
				member, read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)
			return await ctx.send(f"**{member.mention} has been allowed!**")


		await ctx.send("**This is not your room, so you cannot allow someone in it!**")

	@commands.command(aliases=['prohibit'])
	async def forbid(self, ctx, member: discord.Member = None):
		'''
		Forbids a member from joining your channels.
		:param member: The member to forbid.
		'''
		if not member:
			return await ctx.send("**Inform a member to forbid!**")

		user_galaxy = await self.get_galaxy_txt(ctx.author.id, ctx.channel.category.id)
		if user_galaxy:
			user_category = discord.utils.get(ctx.guild.categories, id=user_galaxy[0][1])
			await user_category.set_permissions(
				member, read_messages=False, send_messages=False, connect=False, speak=False, view_channel=False)
			return await ctx.send(f"**{member.mention} has been forbidden!**")

		await ctx.send("**This is not your room, so you cannot forbid someone from it!**")

	async def get_user_vc_timestamp(self, user_id: int, the_time: int):
		mycursor, db = await the_data_base()
		await mycursor.execute(f'SELECT * FROM UserVCstamp WHERE user_id = {user_id}')
		user = await mycursor.fetchall()
		await mycursor.close()
		if not user:
			await self.insert_user_vc(user_id, the_time)
			return await self.get_user_vc_timestamp(user_id, the_time)

		return user[0][1]

	async def insert_user_vc(self, user_id: int, the_time: int):
		mycursor, db = await the_data_base()
		await mycursor.execute("INSERT INTO UserVCstamp (user_id, user_vc_ts) VALUES (%s, %s)", (user_id, the_time - 61))
		await db.commit()
		await mycursor.close()

	async def update_user_vc_ts(self, user_id: int, new_ts: int):
		mycursor, db = await the_data_base()
		await mycursor.execute(f"UPDATE UserVCstamp SET user_vc_ts = {new_ts} WHERE user_id = {user_id}")
		await db.commit()
		await mycursor.close()

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def create_table_user_vc_ts(self, ctx):
		'''
		(ADM) Creates the UserVcstamp table.
		'''
		await ctx.message.delete()
		if await self.table_user_vc_ts_exists():
			return await ctx.send("**Table __UserVCstamp__ already exists!**")
		mycursor, db = await the_data_base()
		await mycursor.execute("CREATE TABLE UserVCstamp (user_id bigint, user_vc_ts bigint)")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __UserVCstamp__ created!**", delete_after=5)

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def drop_table_user_vc_ts(self, ctx):
		'''
		(ADM) Drops the UserVcstamp table.
		'''
		await ctx.message.delete()
		if not await self.table_user_vc_ts_exists():
			return await ctx.send("**Table __UserVCstamp__ doesn't exist!**")
		mycursor, db = await the_data_base()
		await mycursor.execute("DROP TABLE UserVCstamp")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __UserVCstamp__ dropped!**", delete_after=5)

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def reset_table_user_vc_ts(self, ctx):
		'''
		(ADM) Resets the UserVcstamp table.
		'''
		await ctx.message.delete()
		if not await self.table_user_vc_ts_exists():
			return await ctx.send("**Table __UserVCstamp__ doesn't exist yet!**")
		mycursor, db = await the_data_base5()
		await mycursor.execute("DELETE FROM UserVCstamp")
		await db.commit()
		await mycursor.close()
		return await ctx.send("**Table __UserVCstamp__ reset!**", delete_after=5)

	async def table_user_vc_ts_exists(self):
		mycursor, db = await the_data_base5()
		await mycursor.execute(f"SHOW TABLE STATUS LIKE 'UserVCstamp'")
		table_info = await mycursor.fetchall()
		await mycursor.close()
		if len(table_info) == 0:
			return False

		else:
			return True

def setup(client):
	client.add_cog(CreateSmartRoom(client))