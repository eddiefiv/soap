import discord

def make_embed(title, color, desc = ""):
    return discord.Embed(
        color = color,
        title = title,
        description = desc,
        type = 'rich'
    )

async def send_msg(context, message = None, embed: discord.Embed = None, view = None, delete_after = None, ephemeral = False, defer = True):
    if type(context) == discord.Interaction:
        if ephemeral:
            ret = await context.response.send_message(content = message, embed = embed, view = view, delete_after = delete_after, ephemeral = True)
        else:
            if defer:
                await context.response.defer(thinking = True)
            if embed != None and view != None:
                if defer:
                    ret = await context.followup.send(content = message, embed = embed, view = view)
                else:
                    ret = await context.channel.send(content = message, embed = embed, view = view)
            if embed != None and view != None:
                if defer:
                    ret = await context.followup.send(content = message, embed = embed, view = view)
                else:
                    ret = await context.channel.send(content = message, embed = embed, view = view)
            elif embed != None and view == None:
                if defer:
                    ret = await context.followup.send(content = message, embed = embed)
                else:
                    ret = await context.channel.send(content = message, embed = embed, view = view)
            elif embed == None and view != None:
                if defer:
                    ret = await context.followup.send(content = message, view = view)
                else:
                    ret = await context.channel.send(content = message, embed = embed, view = view)
            else:
                if defer and message != None:
                    ret = await context.followup.send(content = message)
                elif message != None:
                    ret = await context.channel.send(content = message, embed = embed, view = view)

    return ret