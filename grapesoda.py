import sys
import discord
from discord.ext import commands
from discord.utils import get
import gspread
import json.decoder
# from authlib.client import AssertionSession
from authlib.integrations.requests_client import AssertionSession
from gspread import Client
import time
import asyncio
import sys
import os
from discord import NotFound
from datetime import datetime

# Google Sheets and Discord authentication
with open("settings.json", "r") as jsonFile:
    data = json.load(jsonFile)

discordToken = data['discordToken']
googleAPIKey = data['googleAPIKey']

# Your Google Keyfile Configuration location
keyFileLocation = data['keyFileLocation']

bot_prefix = "."
bot = commands.Bot(command_prefix=bot_prefix)
server_id = data['serverID']
main_channel_id = data['mainChannelID'] # welfare-office
gtw_message_id = data['GTWMessageID']
boruta_message_id = data['borutaMessageID']
giltine_message_id = data['giltineMessageID']
system_message_channel_id = data['systemMsgChannelID'] # system-messages

current_boruta_emoji_allowed = data['currentBorutaEmojiName'] # emoji currently detected for boruta
current_gtw_emoji_allowed = data['currentGTWEmojiName'] # emoji currently detected for gtw
current_giltine_emoji_allowed = data['currentGiltineEmojiName'] # emoji currently detected for gtw

bot_owner_id = data['botOwnerID'] # owner id (for .restart command)

scope = None
credentials = None
gc = None
sht1 = None
worksheetSettings = None
discordID = None
main_channel = None
message = None
reactGTWSheet = None
reactBorutaSheet = None
reactGiltineSheet = None
data = None

tempReactBorutaSheet = None
tempReactGTWSheet = None
tempReactGiltineSheet = None

allowedRoles1 = ['Engineer']
allowedRoles2 = ['Engineer', 'Vice Soda', 'Management Department']
allowedRoles3 = ['Niglets', 'Generals']

allowedChannels = [system_message_channel_id]

@bot.event
async def on_ready():
    server_on_ready = bot.get_guild(id=int(server_id))
    main_channel_id_on_ready = bot.get_channel(int(main_channel_id))
    system_message_channel_on_ready = bot.get_channel(int(system_message_channel_id))
    
    divider()
    print("Bot Name: %s" % bot.user.name)
    print("Bot ID: %s" % str(bot.user.id))
    print("Discord Version: %s" % str(discord.__version__))
    print("Discord Token: %s" % discordToken)
    print("Google API Token: %s" % googleAPIKey)
    divider()
    print("Server: %s" % str(server_on_ready))
    print("Main Channel: #%s" % str(main_channel_id_on_ready))
    print("System Messages Channel: #%s" % str(system_message_channel_on_ready))

    if authWithAuthLib() == 1:
        divider()
        print("Authentication successful.")
        await system_message_channel_on_ready.send('Bot is online.')
    else:
        divider()
        print("Authentication failed.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command(pass_context=True)
async def restart(ctx):
    system_message_channel = bot.get_channel(int(system_message_channel_id))
    if str(ctx.author.id) == str(bot_owner_id):
        print("Bot is restarting...")
        # await ctx.author.send('Bot is restarting...')
        await system_message_channel.send('Bot is restarting...')
        os.execv(sys.executable, ['python'] + sys.argv)

@bot.command(pass_context=True)
async def spreadsheet(ctx):
    if checkRoles(ctx, allowedRoles3) == 1:    
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        await system_message_channel.send("Spreadsheet link here: %s" % str('https://docs.google.com/spreadsheets/d/1lG3mW4FyxPUQQOQ1Z_6gRC6W3mFDtMq6ADzbmauQVHI/edit?usp=sharing'))

@bot.command(pass_context=True)
async def test5(ctx):
    if checkRoles(ctx, allowedRoles3) == 1:    
        server = bot.get_guild(id=int(server_id))

        a = set()
        if server:
            for member in server.members:
                for roles in member.roles:
                    if str(roles) == 'Niglets':
                        a.add(str(member.id))

        print(a)

        values_from_discord_sheet = discordID.col_values(1)
        del values_from_discord_sheet[0]

        b = set(values_from_discord_sheet)
        print(b)

        print("set a size %s" % len(a))
        print("set b size %s" % len(b))

        diffSet = b-a

        for val in diffSet:
            cell = discordID.find(str(val))
            values_in_row = discordID.row_values(cell.row)
            print(values_in_row)

@bot.command(pass_context=True)
async def commands(ctx):
    if checkRoles(ctx, allowedRoles3) == 1:    
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        statusEmbed = discord.Embed(title="Commands List", color=0xF08080)
        statusEmbed.add_field(name='.boruta', value='Do a full refresh of newly added/removed members from the Boruta React list', inline=True)
        statusEmbed.add_field(name='.giltine', value='Do a full refresh of newly added/removed members from the Giltine React list', inline=True)
        statusEmbed.add_field(name='.gtw', value='Do a full refresh of newly added/removed members from the GTW React list', inline=True)
        statusEmbed.add_field(name='.refresh', value='Force refresh update on all discord ID sheet information and automatically insert new members/remove old members', inline=False)
        statusEmbed.add_field(name='.spreadsheet', value='URL to the spreadsheet (View-only)', inline=False)
        statusEmbed.add_field(name='.msgid status', value='Show the message IDs of Boruta, Giltine and GTW', inline=True)
        statusEmbed.add_field(name='.msgid (boruta/giltine/gtw) (id)', value='Update the messageID so that the bot can recognise the react from the specified id', inline=True)
        statusEmbed.add_field(name='.emoji (boruta/giltine/gtw) (emoji name)', value='Change the emoji detected for .boruta / .giltine / .gtw command', inline=True)
        await system_message_channel.send(embed=statusEmbed)

@bot.command(pass_context=True)
async def emoji(ctx, arg1, arg2):
    if checkRoles(ctx, allowedRoles2) == 1:    
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        data = readJSON()

        if arg1 == 'boruta':
            data['currentBorutaEmojiName'] = arg2
            writeJSON(data)
            await system_message_channel.send("Emoji detected for .boruta command is set to %s" % str(arg2))
        elif arg1 == 'gtw':
            data['currentGTWEmojiName'] = arg2
            writeJSON(data)
            await system_message_channel.send("Emoji detected for .gtw command is set to %s" % str(arg2))
        elif arg1 == 'giltine':
            data['currentGiltineEmojiName'] = arg2
            writeJSON(data)
            await system_message_channel.send("Emoji detected for .giltine command is set to %s" % str(arg2))

@bot.command(pass_context=True)
async def msgid(ctx, *args):
    if checkRoles(ctx, allowedRoles2) == 1:    
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        main_channel = bot.get_channel(int(main_channel_id))
        msg1 = None
        msg2 = None
        msg3 = None
        msg4 = None
        msg5 = None
        msg6 = None
        data = readJSON()
        if args[0] == 'boruta':
            prevBorutaMessageID = data['borutaMessageID']
            currBorutaMessageID = args[1]

            data['borutaMessageID'] = currBorutaMessageID

            writeJSON(data)

            try:
                msg1 = await main_channel.fetch_message(prevBorutaMessageID)
                msg1Content = msg1.content
                msg1Author = msg1.author.name
                print("prevBorutaMessageID: " + str(msg1Content))
            except discord.NotFound:
                print("prevBorutaMessageID: Message not found")
                msg1Content = "Not found"
                msg1Author = "No user"

            try:
                msg2 = await main_channel.fetch_message(currBorutaMessageID)
                msg2Content = msg2.content
                msg2Author = msg2.author.name
                print("currBorutaMessageID: " + str(msg2Content))
            except discord.NotFound:
                print("currBorutaMessageID: Message not found")
                msg2Content = "Not found"
                msg2Author = "No user"
                                
            await system_message_channel.send("Boruta MessageID Changed:")
            await system_message_channel.send("Previous Message by %s: %s (%s)" % (msg1Author, msg1Content, prevBorutaMessageID))
            await system_message_channel.send("Current Message by %s: %s (%s)" % (msg2Author, msg2Content, currBorutaMessageID))
        elif args[0] == 'giltine':
            prevGiltineMessageID = data['giltineMessageID']
            currGiltineMessageID = args[1]
            data['giltineMessageID'] = currGiltineMessageID
            writeJSON(data)

            try:
                msg3 = await main_channel.fetch_message(prevGiltineMessageID)
                msg3Content = msg3.content
                msg3Author = msg3.author.name
                print("prevGiltineMessageID: " + str(msg3Content))
            except discord.NotFound:
                print("prevGiltineMessageID: Message not found")
                msg3Content = "Not found"
                msg3Author = "No user"

            try:
                msg4 = await main_channel.fetch_message(currGiltineMessageID)
                msg4Content = msg4.content
                msg4Author = msg4.author.name
                print("currGiltineMessageID: " + str(msg4Content))
            except discord.NotFound:
                print("currGiltineMessageID: Message not found")
                msg4Content = "Not found"
                msg4Author = "No user"
                                
            await system_message_channel.send("Giltine MessageID Changed:")
            await system_message_channel.send("Previous Message by %s: %s (%s)" % (msg3Author, msg3Content, prevGiltineMessageID))
            await system_message_channel.send("Current Message by %s: %s (%s)" % (msg4Author, msg4Content, currGiltineMessageID))
        elif args[0] == 'gtw':
            prevGTWMessageID = data['GTWMessageID']
            currGTWMessageID = args[1]
            data['GTWMessageID'] = currGTWMessageID
            writeJSON(data)

            try:
                msg5 = await main_channel.fetch_message(prevGTWMessageID)
                msg5Content = msg5.content
                msg5Author = msg5.author.name
                print("prevGTWMessageID: " + str(msg5Content))
            except discord.NotFound:
                print("prevGTWMessageID: Message not found")
                msg5Content = "Not found"
                msg5Author = "No user"

            try:
                msg6 = await main_channel.fetch_message(currGTWMessageID)
                msg6Content = msg6.content
                msg6Author = msg6.author.name
                print("currGTWMessageID: " + str(msg6Content))
            except discord.NotFound:
                print("currGTWMessageID: Message not found")
                msg6Content = "Not found"
                msg6Author = "No user"
                                
            await system_message_channel.send("GTW MessageID Changed:")
            await system_message_channel.send("Previous Message by %s: %s (%s)" % (msg5Author, msg5Content, prevGTWMessageID))
            await system_message_channel.send("Current Message by %s: %s (%s)" % (msg6Author, msg6Content, currGTWMessageID))
        elif args[0] == 'status':
            statusEmbed = discord.Embed(title="Message ID and Emoji Name Status", color=0xF08080)
            statusEmbed.add_field(name='Boruta Message ID', value=data['borutaMessageID'], inline=False)
            statusEmbed.add_field(name='Boruta Emoji Name', value=data['currentBorutaEmojiName'], inline=False)
            statusEmbed.add_field(name='Giltine Message ID', value=data['giltineMessageID'], inline=False)
            statusEmbed.add_field(name='Giltine Emoji Name', value=data['currentGiltineEmojiName'], inline=False)
            statusEmbed.add_field(name='GTW Message ID', value=data['GTWMessageID'], inline=False)
            statusEmbed.add_field(name='GTW Emoji Name', value=data['currentGTWEmojiName'], inline=False)
            await system_message_channel.send(embed=statusEmbed)
        else:
            await system_message_channel.send("Invalid arguments")

async def updateCells(users, typeOfReact):

    server_on_ready = bot.get_guild(id=int(server_id))
    niglets_role = discord.utils.get(server_on_ready.roles,name="Niglets")
    system_message_channel = bot.get_channel(int(system_message_channel_id))
    main_channel = bot.get_channel(int(main_channel_id))

    # Hide Nighlets role from viewing channel when processing list
    perms = main_channel.overwrites_for(niglets_role)
    perms.view_channel = False
    await main_channel.set_permissions(niglets_role, overwrite=perms)
    
    if typeOfReact == 'boruta':
        reactBorutaSheet.clear()

        reactBorutaSheet.append_row(['Discord ID', 'Discord Username', 'Changed Discord Nickname', 'Actual Discord Nickname', 'Actual Ingame Nickname'])

        cell_listA = reactBorutaSheet.range('A2:A150')
        cell_listB = reactBorutaSheet.range('B2:B150')
        cell_listC = reactBorutaSheet.range('C2:C150')
        cell_listD = reactBorutaSheet.range('D2:D150')
        cell_listE = reactBorutaSheet.range('E2:E150')
        
        i = 0
        
        originalUsersCount = len(users)
        invalidCount = 0

        for user in users:
            # exitCondition to redo the current item in the case that the user is in server but react is not refreshed yet
            exitCondition = 0
            while exitCondition == 0:
                tempNickname = None
                try:
                    print ("DEBUG: " + str(user))

                    if str(user.nick) == 'None':
                        cell_listC[i].value = str(user.name)
                        tempNickname = str(user.name)
                    else:
                        cell_listC[i].value = str(user.nick)
                        tempNickname = str(user.nick)

                    cell = discordID.find(str(user.id))
                    actualIGN = discordID.cell(cell.row, 5).value
                    
                    cell_listA[i].value = str(user.id)
                    cell_listB[i].value = str(user)
                    cell_listD[i].value = str(user.name)
                    
                    if len(actualIGN) == 0:
                        cell_listE[i].value = "Not known yet"
                    else:
                        cell_listE[i].value = actualIGN

                    # so we can exit the while loop if nothing goes wrong
                    exitCondition = 1
                except gspread.exceptions.CellNotFound:         
                    if server_on_ready.get_member(int(user.id)) is not None:
                        # member is in server
                        print("Member %s is in the server: adding %s into list, and reprocessing this loop" % (str(user.name), str(user.name)))
                        discordID.append_row([str(user.id), str(user), tempNickname, str(user.name), "Not known yet"])
                        await system_message_channel.send("New Niglets %s has reacted to post but is not in Discord ID list, adding the new member to the list." % str(user))
                    else:
                        # member not in server
                        print("Member %s is not in the server" % str(user.name))
                        invalidCount = invalidCount + 1
                        print("updateCells: CellNotFound - %s" % str(user))
                        await system_message_channel.send("Former Niglets %s has reacted to post and left the server, total reacts in server may not match sheet react count." % str())
                except Exception as outliner:
                    invalidCount = invalidCount + 1
                    print("updateCells: outliner Exception - %s" % str(outliner))           
                    await system_message_channel.send("%s is an outlier and there is an issue with the nick or some other unknown error." % str(user))                         

                if exitCondition != 0:
                    i = i + 1
                    if i % 5 == 0:
                        await system_message_channel.send("Processing Boruta react list: %s of %s" % (str(i), str(len(users))))

                print("Processing Boruta react list: %s of %s" % (str(i), str(len(users))))
                await asyncio.sleep(2.5)

        reactBorutaSheet.update_cells(cell_listA)
        reactBorutaSheet.update_cells(cell_listB)
        reactBorutaSheet.update_cells(cell_listC)
        reactBorutaSheet.update_cells(cell_listD)
        reactBorutaSheet.update_cells(cell_listE)

        await system_message_channel.send("Processing Boruta react list completed. %s out of %s reacts are valid." % (str(originalUsersCount - invalidCount), str(originalUsersCount)))        
        print("Processing Boruta react list completed.")
    elif typeOfReact == 'giltine':
        reactGiltineSheet.clear()

        reactGiltineSheet.append_row(['Discord ID', 'Discord Username', 'Changed Discord Nickname', 'Actual Discord Nickname', 'Actual Ingame Nickname'])

        cell_listA = reactGiltineSheet.range('A2:A150')
        cell_listB = reactGiltineSheet.range('B2:B150')
        cell_listC = reactGiltineSheet.range('C2:C150')
        cell_listD = reactGiltineSheet.range('D2:D150')
        cell_listE = reactGiltineSheet.range('E2:E150')
        
        i = 0
                
        originalUsersCount = len(users)
        invalidCount = 0

        for user in users:
            # exitCondition to redo the current item in the case that the user is in server but react is not refreshed yet
            exitCondition = 0
            while exitCondition == 0:
                tempNickname = None
                try:
                    print ("DEBUG: " + str(user))

                    if str(user.nick) == 'None':
                        cell_listC[i].value = str(user.name)
                        tempNickname = str(user.name)
                    else:
                        cell_listC[i].value = str(user.nick)
                        tempNickname = str(user.nick)

                    cell = discordID.find(str(user.id))
                    actualIGN = discordID.cell(cell.row, 5).value
                    
                    cell_listA[i].value = str(user.id)
                    cell_listB[i].value = str(user)
                    cell_listD[i].value = str(user.name)
                    
                    if len(actualIGN) == 0:
                        cell_listE[i].value = "Not known yet"
                    else:
                        cell_listE[i].value = actualIGN

                    # so we can exit the while loop if nothing goes wrong
                    exitCondition = 1
                except gspread.exceptions.CellNotFound:         
                    if server_on_ready.get_member(int(user.id)) is not None:
                        # member is in server
                        print("Member %s is in the server: adding %s into list, and reprocessing this loop" % (str(user.name), str(user.name)))
                        discordID.append_row([str(user.id), str(user), tempNickname, str(user.name), "Not known yet"])
                        await system_message_channel.send("New Niglets %s has reacted to post but is not in Discord ID list, adding the new member to the list." % str(user))
                    else:
                        # member not in server
                        print("Member %s is not in the server" % str(user.name))
                        invalidCount = invalidCount + 1
                        print("updateCells: CellNotFound - %s" % str(user))
                        await system_message_channel.send("Former Niglets %s has reacted to post and left the server, total reacts in server may not match sheet react count." % str())
                except Exception as outliner:
                    invalidCount = invalidCount + 1
                    print("updateCells: outliner Exception - %s" % str(outliner))           
                    await system_message_channel.send("%s is an outlier and there is an issue with the nick or some other unknown error." % str(user))                    

                if exitCondition != 0:
                    i = i + 1
                    if i % 5 == 0:
                        await system_message_channel.send("Processing Giltine react list: %s of %s" % (str(i), str(len(users))))

                print("Processing Giltine react list: %s of %s" % (str(i), str(len(users))))
                await asyncio.sleep(2.5)

        reactGiltineSheet.update_cells(cell_listA)
        reactGiltineSheet.update_cells(cell_listB)
        reactGiltineSheet.update_cells(cell_listC)
        reactGiltineSheet.update_cells(cell_listD)    
        reactGiltineSheet.update_cells(cell_listE)         
    
        await system_message_channel.send("Processing Giltine react list completed. %s out of %s reacts are valid." % (str(originalUsersCount - invalidCount), str(originalUsersCount)))
        print("Processing Giltine react list completed.")
    elif typeOfReact == 'gtw':
        reactGTWSheet.clear()

        reactGTWSheet.append_row(['Discord ID', 'Discord Username', 'Changed Discord Nickname', 'Actual Discord Nickname', 'Actual Ingame Nickname'])

        cell_listA = reactGTWSheet.range('A2:A150')
        cell_listB = reactGTWSheet.range('B2:B150')
        cell_listC = reactGTWSheet.range('C2:C150')
        cell_listD = reactGTWSheet.range('D2:D150')
        cell_listE = reactGTWSheet.range('E2:E150')
        
        i = 0
                
        originalUsersCount = len(users)
        invalidCount = 0

        for user in users:
            # exitCondition to redo the current item in the case that the user is in server but react is not refreshed yet
            exitCondition = 0
            while exitCondition == 0:
                tempNickname = None
                try:
                    print ("DEBUG: " + str(user))
                    if str(user.nick) == 'None':
                        cell_listC[i].value = str(user.name)
                        tempNickname = str(user.name)
                    else:
                        cell_listC[i].value = str(user.nick)
                        tempNickname = str(user.nick)

                    cell = discordID.find(str(user.id))
                    actualIGN = discordID.cell(cell.row, 5).value
                    
                    cell_listA[i].value = str(user.id)
                    cell_listB[i].value = str(user)
                    cell_listD[i].value = str(user.name)
                    
                    if len(actualIGN) == 0:
                        cell_listE[i].value = "Not known yet"
                    else:
                        cell_listE[i].value = actualIGN

                    # so we can exit the while loop if nothing goes wrong
                    exitCondition = 1
                except gspread.exceptions.CellNotFound:         
                    if server_on_ready.get_member(int(user.id)) is not None:
                        # member is in server
                        print("Member %s is in the server: adding %s into list, and reprocessing this loop" % (str(user.name), str(user.name)))
                        discordID.append_row([str(user.id), str(user), tempNickname, str(user.name), "Not known yet"])
                        await system_message_channel.send("New Niglets %s has reacted to post but is not in Discord ID list, adding the new member to the list." % str(user))
                    else:
                        # member not in server
                        print("Member %s is not in the server" % str(user.name))
                        invalidCount = invalidCount + 1
                        print("updateCells: CellNotFound - %s" % str(user))
                        await system_message_channel.send("Former Niglets %s has reacted to post and left the server, total reacts in server may not match sheet react count." % str())
                except Exception as outliner:
                    invalidCount = invalidCount + 1
                    print("updateCells: outliner Exception - %s" % str(outliner))           
                    await system_message_channel.send("%s is an outlier and there is an issue with the nick or some other unknown error." % str(user))                         

                if exitCondition != 0:
                    i = i + 1
                    if i % 5 == 0:
                        await system_message_channel.send("Processing GTW react list: %s of %s" % (str(i), str(len(users))))

                print("Processing GTW react list: %s of %s" % (str(i), str(len(users))))
                await asyncio.sleep(2.5)

        reactGTWSheet.update_cells(cell_listA)
        reactGTWSheet.update_cells(cell_listB)
        reactGTWSheet.update_cells(cell_listC)
        reactGTWSheet.update_cells(cell_listD)    
        reactGTWSheet.update_cells(cell_listE)

        await system_message_channel.send("Processing GTW react list completed. %s out of %s reacts are valid." % (str(originalUsersCount - invalidCount), str(originalUsersCount)))
        print("Processing GTW react list completed.")
    
    perms.view_channel = True
    await main_channel.set_permissions(niglets_role, overwrite=perms)

@bot.command(pass_context=True)
async def boruta(ctx):
    if checkRoles(ctx, allowedRoles2) == 1: 

        data = readJSON()
        boruta_message_id = data['borutaMessageID']

        print("Boruta main channelID is %s" % str(main_channel_id))
        print("Boruta message_id is %s" % str(boruta_message_id))
        main_channel = bot.get_channel(int(main_channel_id))
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        message = await main_channel.fetch_message(boruta_message_id)
        
        await system_message_channel.send("Processing Boruta react list, please wait... ")
        
        users = set()
        for reaction in message.reactions:
            async for user in reaction.users():
                users.add(user)

        print(users)
        await updateCells(users, "boruta")

@bot.command(pass_context=True)
async def gtw(ctx):
    if checkRoles(ctx, allowedRoles2) == 1:    

        data = readJSON()
        gtw_message_id = data['GTWMessageID']

        print("GTW main channelID is %s" % str(main_channel_id))
        print("GTW message_id is %s" % str(gtw_message_id))
        main_channel = bot.get_channel(int(main_channel_id))
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        message = await main_channel.fetch_message(gtw_message_id)
        
        await system_message_channel.send("Processing GTW react list, please wait... ")
        
        users = set()
        for reaction in message.reactions:
            async for user in reaction.users():
                users.add(user)

        print(users)
        await updateCells(users, "gtw")

@bot.command(pass_context=True)
async def giltine(ctx):
    if checkRoles(ctx, allowedRoles2) == 1:    

        data = readJSON()
        giltine_message_id = data['giltineMessageID']

        print("Giltine main channelID is %s" % str(main_channel_id))
        print("Giltine message_id is %s" % str(giltine_message_id))
        main_channel = bot.get_channel(int(main_channel_id))
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        message = await main_channel.fetch_message(giltine_message_id)
        
        await system_message_channel.send("Processing Giltine react list, please wait... ")
        
        users = set()
        for reaction in message.reactions:
            async for user in reaction.users():
                users.add(user)

        print(users)
        await updateCells(users, "giltine")

@bot.event
async def on_raw_reaction_add(payload):

    discordUsername = "Not known yet"
    changedDiscordNickname = "Not known yet"
    actualDiscordNickname = "Not known yet"
    actualIGN = "Not known yet"
    cells = None

    if str(payload.channel_id) == main_channel_id:
        main_channel = bot.get_channel(int(main_channel_id))
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        message = await main_channel.fetch_message(payload.message_id)

        data = readJSON()

        boruta_message_id = data['borutaMessageID']
        giltine_message_id = data['giltineMessageID']
        gtw_message_id = data['GTWMessageID']

        current_boruta_emoji_allowed = data['currentBorutaEmojiName']
        current_giltine_emoji_allowed = data['currentGiltineEmojiName']
        current_gtw_emoji_allowed = data['currentGTWEmojiName']

        borutaSheetFlag = data['borutaSheetFlag']
        GiltineSheetFlag = data['GiltineSheetFlag']
        GTWSheetFlag = data['GTWSheetFlag']

        if (payload.emoji.name == current_boruta_emoji_allowed) or (payload.emoji.name == current_gtw_emoji_allowed) or (payload.emoji.name == current_giltine_emoji_allowed):
            if (str(payload.message_id) == str(boruta_message_id)) and (payload.emoji.name == current_boruta_emoji_allowed):
                discord_id_dict = formula_spreadsheet_information()

                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]                

                    if len(actualDiscordNickname) == 0:
                        actualDiscordNickname = "Not known yet"

                    if len(actualIGN) == 0:
                        actualIGN = "Not known yet"

                    if len(changedDiscordNickname) == 0:
                        changedDiscordNickname = "Not known yet"

                    reactionAddEmbed = discord.Embed(title="(Add) Boruta Reaction", color=0xF08080)
                    reactionAddEmbed.set_thumbnail(url="https://i.imgur.com/8QYWgQL.jpg")
                    reactionAddEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                    reactionAddEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                    reactionAddEmbed.add_field(name='Discord Username', value=str(payload.member), inline=False)
                    reactionAddEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    reactionAddEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))

                    # reactionAddEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                    # final check to ensure it isn't people spamming react
                    try:
                        cell = reactBorutaSheet.find(str(payload.user_id))
                    except gspread.exceptions.CellNotFound:
                        # print("Add Reaction Check Spam: CellNotFound")
                        await system_message_channel.send(embed=reactionAddEmbed)
                        reactBorutaSheet.append_row([str(payload.user_id), str(payload.member), str(changedDiscordNickname), str(actualDiscordNickname), str(actualIGN)])

                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")
                
                try:
                    cells = reactBorutaSheet.findall(str(payload.user_id))

                    if len(cells) > 1:
                        counter = 0
                        for cellValue in cells:
                            if counter != 0:
                                reactBorutaSheet.delete_row(cellValue.row)
                            counter = counter + 1
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Final Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")

                divider()
                print("(Add) Boruta Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(payload.member))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))

            elif (str(payload.message_id) == str(giltine_message_id)) and (payload.emoji.name == current_giltine_emoji_allowed):
                discord_id_dict = formula_spreadsheet_information()

                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]

                    if len(actualDiscordNickname) == 0:
                        actualDiscordNickname = "Not known yet"

                    if len(actualIGN) == 0:
                        actualIGN = "Not known yet"

                    if len(changedDiscordNickname) == 0:
                        changedDiscordNickname = "Not known yet"

                    reactionAddEmbed = discord.Embed(title="(Add) Giltine Reaction", color=0x800000)
                    reactionAddEmbed.set_thumbnail(url="https://i.imgur.com/vmRYz3H.png")
                    reactionAddEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                    reactionAddEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                    reactionAddEmbed.add_field(name='Discord Username', value=str(payload.member), inline=False)
                    reactionAddEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    reactionAddEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))
                    # reactionAddEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                    # final check to ensure it isn't people spamming react
                    try:
                        cell = reactGiltineSheet.find(str(payload.user_id))
                    except gspread.exceptions.CellNotFound:
                        # print("Add Reaction Check Spam: CellNotFound")
                        await system_message_channel.send(embed=reactionAddEmbed)
                        reactGiltineSheet.append_row([str(payload.user_id), str(payload.member), str(changedDiscordNickname), str(actualDiscordNickname), str(actualIGN)])

                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")
                
                try:
                    cells = reactGiltineSheet.findall(str(payload.user_id))

                    if len(cells) > 1:
                        counter = 0
                        for cellValue in cells:
                            if counter != 0:
                                reactGiltineSheet.delete_row(cellValue.row)
                            counter = counter + 1
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Final Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")

                divider()
                print("(Add) Giltine Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(payload.member))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))

            elif (str(payload.message_id) == str(gtw_message_id)) and (payload.emoji.name == current_gtw_emoji_allowed):
                # print ("gtw and payload msg id matches")

                discord_id_dict = formula_spreadsheet_information()

                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]

                    if len(actualDiscordNickname) == 0:
                        actualDiscordNickname = "Not known yet"

                    if len(actualIGN) == 0:
                        actualIGN = "Not known yet"

                    if len(changedDiscordNickname) == 0:
                        changedDiscordNickname = "Not known yet"

                    reactionAddEmbed = discord.Embed(title="(Add) GTW Reaction", color=0x6495ED)
                    reactionAddEmbed.set_thumbnail(url="https://i.imgur.com/pFOCE0f.jpg")
                    reactionAddEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                    reactionAddEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                    reactionAddEmbed.add_field(name='Discord Username', value=str(payload.member), inline=False)
                    reactionAddEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    reactionAddEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))
                    # reactionAddEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                    # reactionAddEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                    # final check to ensure it isn't people spamming react
                    try:
                        cell = reactGTWSheet.find(str(payload.user_id))
                    except gspread.exceptions.CellNotFound:
                        # print("Add Reaction Check Spam: CellNotFound")
                        await system_message_channel.send(embed=reactionAddEmbed)
                        reactGTWSheet.append_row([str(payload.user_id), str(payload.member), str(changedDiscordNickname), str(actualDiscordNickname), str(actualIGN)])

                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")
                
                try:
                    cells = reactGTWSheet.findall(str(payload.user_id))

                    if len(cells) > 1:
                        counter = 0
                        for cellValue in cells:
                            if counter != 0:
                                reactGTWSheet.delete_row(cellValue.row)
                            counter = counter + 1
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Final Add Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Add Reaction: NoneType")

                divider()
                print("(Add) GTW Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(payload.member))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))

@bot.event
async def on_raw_reaction_remove(payload):

    discordUsername = "Not known yet"
    changedDiscordNickname = "Not known yet"
    actualDiscordNickname = "Not known yet"
    actualIGN = "Not known yet"
    data = readJSON()

    borutaSheetFlag = data['borutaSheetFlag']
    GiltineSheetFlag = data['GiltineSheetFlag']
    GTWSheetFlag = data['GTWSheetFlag']
    
    boruta_message_id = data['borutaMessageID']
    giltine_message_id = data['giltineMessageID']
    gtw_message_id = data['GTWMessageID']

    current_boruta_emoji_allowed = data['currentBorutaEmojiName']
    current_giltine_emoji_allowed = data['currentGiltineEmojiName']
    current_gtw_emoji_allowed = data['currentGTWEmojiName']
    
    if str(payload.channel_id) == main_channel_id:
        main_channel = bot.get_channel(int(main_channel_id))
        system_message_channel = bot.get_channel(int(system_message_channel_id))
        message = await main_channel.fetch_message(payload.message_id)
        if (payload.emoji.name == current_boruta_emoji_allowed) or (payload.emoji.name == current_gtw_emoji_allowed) or (payload.emoji.name == current_giltine_emoji_allowed):
            if (str(payload.message_id) == str(boruta_message_id)) and (payload.emoji.name == current_boruta_emoji_allowed):

                discord_id_dict = formula_spreadsheet_information()        
                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    discordUsername = cell[1]
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]         
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Remove Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Remove Reaction: NoneType")

                if len(discordUsername) == 0:
                    discordUsername = "Not known yet"

                if len(changedDiscordNickname) == 0:
                    changedDiscordNickname = "Not known yet"

                if len(actualDiscordNickname) == 0:
                    actualDiscordNickname = "Not known yet"

                if len(actualIGN) == 0:
                    actualIGN = "Not known yet"

                reactionRemoveEmbed = discord.Embed(title="(Remove) Boruta Reaction", color=0xF08080)
                reactionRemoveEmbed.set_thumbnail(url="https://i.imgur.com/8QYWgQL.jpg")
                reactionRemoveEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                reactionRemoveEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Username', value=str(discordUsername), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                reactionRemoveEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))
                # reactionRemoveEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                try:
                    cell = reactBorutaSheet.find(str(payload.user_id))
                    reactBorutaSheet.delete_row(cell.row)
                    await system_message_channel.send(embed=reactionRemoveEmbed)

                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")

                divider()
                print("(Remove) Boruta Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(discordUsername))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))
            elif (str(payload.message_id) == str(giltine_message_id)) and (payload.emoji.name == current_giltine_emoji_allowed):            
                discord_id_dict = formula_spreadsheet_information()       	
                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    discordUsername = cell[1]
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]    
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Remove Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Remove Reaction: NoneType")

                if len(discordUsername) == 0:
                    discordUsername = "Not known yet"

                if len(changedDiscordNickname) == 0:
                    changedDiscordNickname = "Not known yet"

                if len(actualDiscordNickname) == 0:
                    actualDiscordNickname = "Not known yet"

                if len(actualIGN) == 0:
                    actualIGN = "Not known yet"
                    
                reactionRemoveEmbed = discord.Embed(title="(Remove) Giltine Reaction", color=0x800000)
                reactionRemoveEmbed.set_thumbnail(url="https://i.imgur.com/vmRYz3H.png")
                reactionRemoveEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                reactionRemoveEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Username', value=str(discordUsername), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                reactionRemoveEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))
                # reactionRemoveEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                try:
                    cell = reactGiltineSheet.find(str(payload.user_id))
                    reactGiltineSheet.delete_row(cell.row)
                    await system_message_channel.send(embed=reactionRemoveEmbed)
                        
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")

                divider()
                print("(Remove) Giltine Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(discordUsername))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))                
            elif (str(payload.message_id) == str(gtw_message_id)) and (payload.emoji.name == current_gtw_emoji_allowed):            
                discord_id_dict = formula_spreadsheet_information()       	
                try:
                    cell = discord_id_dict.get(str(payload.user_id))
                    discordUsername = cell[1]
                    actualDiscordNickname = cell[3]
                    actualIGN = cell[4]
                    changedDiscordNickname = cell[2]    
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Remove Reaction: CellNotFound")
                except AttributeError: # NoneType
                    print("Remove Reaction: NoneType")

                if len(discordUsername) == 0:
                    discordUsername = "Not known yet"

                if len(changedDiscordNickname) == 0:
                    changedDiscordNickname = "Not known yet"

                if len(actualDiscordNickname) == 0:
                    actualDiscordNickname = "Not known yet"

                if len(actualIGN) == 0:
                    actualIGN = "Not known yet"
                    
                reactionRemoveEmbed = discord.Embed(title="(Remove) GTW Reaction", color=0x6495ED)
                reactionRemoveEmbed.set_thumbnail(url="https://i.imgur.com/pFOCE0f.jpg")
                reactionRemoveEmbed.add_field(name='Actual IGN', value=str(actualIGN), inline=False)
                reactionRemoveEmbed.add_field(name='Discord ID', value=str(payload.user_id), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Username', value=str(discordUsername), inline=False)
                reactionRemoveEmbed.add_field(name='Discord Nickname', value=str(changedDiscordNickname), inline=False)
                reactionRemoveEmbed.set_footer(text="Total number of reactions: " + str(message.reactions[0].count))
                # reactionRemoveEmbed.add_field(name='Changed Discord Nickname', value=str(changedDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Actual Discord Nickname', value=str(actualDiscordNickname), inline=False)
                # reactionRemoveEmbed.add_field(name='Emoji Name', value=str(payload.emoji.name), inline=False)

                try:
                    cell = reactGTWSheet.find(str(payload.user_id))
                    reactGTWSheet.delete_row(cell.row)
                    await system_message_channel.send(embed=reactionRemoveEmbed)
                        
                except gspread.exceptions.CellNotFound:  # or except gspread.CellNotFound:
                    print("Add Reaction: CellNotFound")

                divider()
                print("(Remove) GTW Reaction")
                print("Actual IGN: %s" % str(actualIGN))
                print("Discord ID: %s" % str(payload.user_id))
                print("Discord Username: %s" % str(discordUsername))
                print("Changed Discord Nickname: %s" % str(changedDiscordNickname))
                print("Actual Discord Nickname: %s" % str(actualDiscordNickname))                

@bot.command(pass_context=True)
async def refresh(ctx):
    system_message_channel = bot.get_channel(int(system_message_channel_id))

    tempNickname = None

    if checkRoles(ctx, allowedRoles2) == 1:    
        await system_message_channel.send("Processing roles list...")
        server = bot.get_guild(id=int(server_id))

        discord_id_dict = formula_spreadsheet_information()

        i = 0
        batch_update_array = []
        range_to_update = None
        serverListSet = set()
        if server:
            for member in server.members:
                members_flag = 0
                for roles in member.roles:
                    retrieve_key_value = discord_id_dict.get(str(member.id)) # retrieve key value based on member id
                    if str(roles) == 'Niglets':
                        serverListSet.add(str(member.id))
                        members_flag = 1
                        if str(member.nick) == 'None':
                            tempNickname = str(member.name)
                        else:
                            tempNickname = str(member.nick)
                            
                        # if user has Niglets role that does not exist in excel then append
                        if retrieve_key_value == None:
                            discordID.append_row([str(member.id), str(member), tempNickname, str(member.name), "Not known yet"])
                            await system_message_channel.send("Niglets added: %s (%s) - %s" % (str(tempNickname), str(member.id), str(member)))
                        else: # if existing member attempt to update
                            try:
                                cell = discordID.find(str(member.id)) # have to call api again as delete_row may shift row position
                                cell_row_number = cell.row                  

                                cell_range_to_update = discordID.range('A' + str(cell_row_number) + ':E' + str(cell_row_number))

                                cell_values = [str(member.id), str(member), tempNickname, str(member.name), retrieve_key_value[4]]

                                for m, val in enumerate(cell_values):
                                    cell_range_to_update[m].value = val

                                discordID.update_cells(cell_range_to_update)
                            except gspread.exceptions.CellNotFound:
                                print("Existing member attempt to update: CellNotFound, skipping")
                        break

                if (members_flag == 0): # not Niglets
                    print ("Not Niglets role, checking the entire excel if the person still exist inside, may be old member or not a member") 

                    if str(member.nick) == 'None':
                        tempNickname = str(member.name)
                    else:
                        tempNickname = str(member.nick)                   
                    retrieve_non_niglets_value = discord_id_dict.get(str(member.id))          
                             
                    if retrieve_non_niglets_value != None: # If not None means it exist therefore attempt to delete it
                        # have to call api again as delete_row may shift row position
                        try:
                            cell = discordID.find(str(member.id))
                            cell_row_number = cell.row
                            discordID.delete_row(cell_row_number)
                            await system_message_channel.send("Niglets removed: %s (%s) - %s" % (str(tempNickname), str(member.id), str(member)))
                        except gspread.exceptions.CellNotFound:
                            print("Attempt to delete member: CellNotFound, skipping")
                else:
                    await asyncio.sleep(2.5)

                i = i + 1
                if i % 50 == 0:
                    await system_message_channel.send("Processing roles list: %s of %s" % (str(i), str(len(server.members))))
                print("Processing roles list: %s of %s >>> %s (%s) - %s" % (str(i), str(len(server.members)), str(tempNickname), str(member.id), str(member)))

        await system_message_channel.send("Doing final check of roles list, removing members no longer in server...")
        print("Doing final check of roles list, removing members no longer in server...")

        values_from_discord_sheet = discordID.col_values(1)
        del values_from_discord_sheet[0]

        discordIDSet = set(values_from_discord_sheet)
        print(discordIDSet)

        print("set serverListSet size %s" % len(serverListSet))
        print("set discordIDSet size %s" % len(discordIDSet))
        
        diffBetweenSet = discordIDSet-serverListSet

        print(diffBetweenSet)

        for diffVal in diffBetweenSet:
            cell = discordID.find(str(diffVal))
            values_in_row = discordID.row_values(cell.row)
            print(values_in_row)
            discordID.delete_row(cell.row)
            await system_message_channel.send("Niglets removed: %s (%s) - %s" % (values_in_row[2], values_in_row[0], values_in_row[1]))

        await system_message_channel.send("Processing roles list completed.")
        print("Processing roles list completed.")

def readJSON():
    global data
    with open("settings.json", "r") as jsonFile:
        data = json.load(jsonFile)
    return data

def writeJSON(data):
    with open("settings.json", "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)

def checkRoles(ctx, selectedRoles):
    rolesFlag = 0
    allowedRoles = selectedRoles

    for roles in allowedRoles:
        role = discord.utils.get(ctx.guild.roles, name=roles)

        if role in ctx.author.roles:
            print('Role found: ' + str(role))
            rolesFlag = 1
            break
    return rolesFlag

# This function gets the entire Discord ID sheet information
def formula_spreadsheet_information():
    all_values_list = discordID.get_all_values() # get all cells of sheet
    discord_id_dict = {} # initialize discord id dictionary

    row_value = 1
    for values in all_values_list:
        if row_value != 1:
            values.append(row_value) # append row number
            discord_id_dict[values[0]] = values 
        row_value = row_value + 1
    return discord_id_dict

# Authenticate using Autolib AssertionSession over oauth2client
# https://blog.authlib.org/2018/authlib-for-gspread
def authWithAuthLib():
    global scope
    global credentials
    global gc
    global sht1
    global worksheetSettings
    global discordID

    global reactGTWSheet
    global reactBorutaSheet
    global reactGiltineSheet
    global worksheetSettings

    global channel
    global message
    
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive',
        ]

        # Keyfile from Google Configuration
        session = create_assertion_session(keyFileLocation, scope)

        gc = Client(None, session)

        sht1 = gc.open_by_key(googleAPIKey)

        worksheet_list = sht1.worksheets()

        reactGTWSheet = sht1.worksheet("GTW React")
        reactGiltineSheet = sht1.worksheet("Giltine React")
        reactBorutaSheet = sht1.worksheet("Boruta React")
        discordID = sht1.worksheet("Discord ID")
        # tempReactBorutaSheet = sht1.worksheet("Temporary Boruta React")
        # tempReactGTWSheet = sht1.worksheet("Temporary GTW React")

        return 1
    except Exception as e:
        print(str(e))
        return 0

def create_assertion_session(conf_file, scopes, subject=None):
    with open(conf_file, 'r') as f:
        conf = json.load(f)

    token_url = conf['token_uri']
    issuer = conf['client_email']
    key = conf['private_key']
    key_id = conf.get('private_key_id')

    header = {'alg': 'RS256'}
    if key_id:
        header['kid'] = key_id

    # Google puts scope in payload
    claims = {'scope': ' '.join(scopes)}
    return AssertionSession(
        grant_type=AssertionSession.JWT_BEARER_GRANT_TYPE,
        token_endpoint=token_url,
        issuer=issuer,
        audience=token_url,
        claims=claims,
        subject=subject,
        key=key,
        header=header,
    )

def divider():
    divider = "--------------------------------------------------------------------------------"
    print(divider)

bot.run(discordToken)