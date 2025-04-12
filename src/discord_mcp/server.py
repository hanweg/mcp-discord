import asyncio
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional
import json

import discord
from discord.ext import commands
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmptyResult, TextContent, Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")

# Discord bot setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize MCP server
app = Server("discord-server")

# Store Discord client reference
discord_client = None

@bot.event
async def on_ready():
    global discord_client
    discord_client = bot
    logger.info(f"Logged in as {bot.user.name}")

# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not discord_client:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)
    return wrapper

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Discord tools."""
    # Define a common message schema for reuse
    message_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Message content"
            },
            "embeds": {
                "type": "array",
                "description": "Array of embed objects to attach to the message",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Embed title"},
                        "description": {"type": "string", "description": "Embed description"},
                        "url": {"type": "string", "description": "URL for embed title"},
                        "color": {"type": "integer", "description": "Color code for the embed (decimal value)"},
                        "timestamp": {"type": "string", "description": "ISO8601 timestamp"},
                        "footer": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "icon_url": {"type": "string"}
                            }
                        },
                        "thumbnail": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}}
                        },
                        "image": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}}
                        },
                        "author": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "url": {"type": "string"},
                                "icon_url": {"type": "string"}
                            }
                        },
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"},
                                    "inline": {"type": "boolean"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "anyOf": [
            {"required": ["content"]},
            {"required": ["embeds"]}
        ]
    }
    
    return [
        # Server Information Tools
        Tool(
            name="list_servers",
            description="Get a list of all Discord servers the bot has access to with their details such as name, id, member count, and creation date.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_members",
            description="Get a list of members in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),

        # Role Management Tools
        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to add role to"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to add"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to remove"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        # Channel Management Tools
        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Channel name"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deletion"
                    }
                },
                "required": ["channel_id"]
            }
        ),

        # Message Reaction Tools
        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)"
                        },
                        "description": "List of emojis to add as reactions"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }
        ),
        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    **message_schema["properties"]
                },
                "required": ["channel_id"],
                "anyOf": message_schema["anyOf"]
            }
        ),
        Tool(
            name="read_messages",
            description="Read recent messages from a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="get_user_info",
            description="Get information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320  # Max 4 weeks
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        
        # DM Tools
        Tool(
            name="send_dm",
            description="Send a direct message to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID to send DM to"
                    },
                    **message_schema["properties"]
                },
                "required": ["user_id"],
                "anyOf": message_schema["anyOf"]
            }
        ),
        Tool(
            name="dm_conversation",
            description="Send a direct message to a user and wait for their response",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID to send DM to"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Maximum time to wait for response in seconds",
                        "default": 60
                    },
                    **message_schema["properties"]
                },
                "required": ["user_id"],
                "anyOf": message_schema["anyOf"]
            }
        )
    ]

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle Discord tool calls."""
    
    if name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        # Prepare kwargs for message sending
        kwargs = {}
        if "content" in arguments:
            kwargs["content"] = arguments["content"]
        
        # Handle embeds if provided
        if "embeds" in arguments and arguments["embeds"]:
            embeds = []
            for embed_data in arguments["embeds"]:
                embed = discord.Embed()
                
                # Set basic embed properties
                if "title" in embed_data:
                    embed.title = embed_data["title"]
                if "description" in embed_data:
                    embed.description = embed_data["description"]
                if "url" in embed_data:
                    embed.url = embed_data["url"]
                if "color" in embed_data:
                    embed.color = embed_data["color"]
                if "timestamp" in embed_data and embed_data["timestamp"]:
                    embed.timestamp = datetime.fromisoformat(embed_data["timestamp"])
                
                # Set author if provided
                if "author" in embed_data:
                    name = embed_data["author"].get("name", "")
                    url = embed_data["author"].get("url", None)
                    icon_url = embed_data["author"].get("icon_url", None)
                    embed.set_author(name=name, url=url, icon_url=icon_url)
                
                # Set footer if provided
                if "footer" in embed_data:
                    text = embed_data["footer"].get("text", "")
                    icon_url = embed_data["footer"].get("icon_url", None)
                    embed.set_footer(text=text, icon_url=icon_url)
                
                # Set thumbnail if provided
                if "thumbnail" in embed_data and "url" in embed_data["thumbnail"]:
                    embed.set_thumbnail(url=embed_data["thumbnail"]["url"])
                
                # Set image if provided
                if "image" in embed_data and "url" in embed_data["image"]:
                    embed.set_image(url=embed_data["image"]["url"])
                
                # Add fields if provided
                if "fields" in embed_data:
                    for field in embed_data["fields"]:
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False)
                        )
                
                embeds.append(embed)
            
            kwargs["embeds"] = embeds
        
        message = await channel.send(**kwargs)
        return [TextContent(
            type="text",
            text=f"Message sent successfully. Message ID: {message.id}"
        )]

    elif name == "read_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 10)), 100)
        fetch_users = arguments.get("fetch_reaction_users", False)  # Only fetch users if explicitly requested
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = []
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji.name) if hasattr(reaction.emoji, 'name') and reaction.emoji.name else str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(reaction.emoji)
                reaction_info = {
                    "emoji": emoji_str,
                    "count": reaction.count
                }
                logger.error(f"Emoji: {emoji_str}")
                reaction_data.append(reaction_info)
            
            # Process embeds explicitly to ensure all data is captured
            embed_dicts = []
            for embed in message.embeds:
                embed_dict = {
                    "title": embed.title,
                    "description": embed.description,
                    "url": embed.url,
                    "color": embed.color.value if embed.color else None,
                    "timestamp": embed.timestamp.isoformat() if embed.timestamp else None,
                    "fields": [
                        {
                            "name": field.name,
                            "value": field.value,
                            "inline": field.inline
                        } for field in embed.fields
                    ]
                }
                
                # Handle author
                if embed.author:
                    embed_dict["author"] = {
                        "name": embed.author.name,
                        "url": embed.author.url,
                        "icon_url": embed.author.icon_url
                    }
                
                # Handle footer
                if embed.footer:
                    embed_dict["footer"] = {
                        "text": embed.footer.text,
                        "icon_url": embed.footer.icon_url
                    }
                
                # Handle images
                if embed.thumbnail:
                    embed_dict["thumbnail"] = {"url": embed.thumbnail.url}
                
                if embed.image:
                    embed_dict["image"] = {"url": embed.image.url}
                
                embed_dicts.append(embed_dict)

            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data,  # Add reactions to message dict
                "embeds": embed_dicts  # Add embeds to message dict
            })
        
        # Format the output string
        message_lines = []
        for m in messages:
            reactions_str = (
                ", ".join([f"{r['emoji']}({r['count']})" for r in m["reactions"]])
                if m["reactions"]
                else "No reactions"
            )
            
            # Format embeds more clearly
            embeds_str = ""
            if m['embeds']:
                embeds_str = "\nEmbeds:"
                for i, embed in enumerate(m['embeds']):
                    embeds_str += f"\n  Embed {i+1}:"
                    if embed.get('title'):
                        embeds_str += f"\n    Title: {embed['title']}"
                    if embed.get('description'):
                        embeds_str += f"\n    Description: {embed['description']}"
                    if embed.get('url'):
                        embeds_str += f"\n    URL: {embed['url']}"
                    if embed.get('color'):
                        embeds_str += f"\n    Color: {embed['color']}"
                    if embed.get('timestamp'):
                        embeds_str += f"\n    Timestamp: {embed['timestamp']}"
                    
                    if embed.get('author'):
                        embeds_str += f"\n    Author: {embed['author'].get('name', '')}"
                    
                    if embed.get('footer'):
                        embeds_str += f"\n    Footer: {embed['footer'].get('text', '')}"
                    
                    if embed.get('thumbnail'):
                        embeds_str += f"\n    Thumbnail: {embed['thumbnail'].get('url', '')}"
                    
                    if embed.get('image'):
                        embeds_str += f"\n    Image: {embed['image'].get('url', '')}"
                    
                    if embed.get('fields'):
                        embeds_str += "\n    Fields:"
                        for field in embed['fields']:
                            embeds_str += f"\n      {field['name']}: {field['value']} ({'Inline' if field.get('inline') else 'Not inline'})"
            
            message_lines.append(
                f"{m['author']} ({m['timestamp']}): {m['content']}\n"
                f"Reactions: {reactions_str}"
                f"{embeds_str}" 
            )
        
        output_text = f"Retrieved {len(messages)} messages:\n\n" + "\n━━━━━━━━━━━━━━━━━━━━━━\n".join(message_lines) # Separator for clarity

        return [TextContent(
            type="text",
            text=output_text
        )]

    elif name == "get_user_info":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        user_info = {
            "id": str(user.id),
            "name": user.name,
            "discriminator": user.discriminator,
            "bot": user.bot,
            "created_at": user.created_at.isoformat()
        }
        return [TextContent(
            type="text",
            text=f"User information:\n" + 
                 f"Name: {user_info['name']}#{user_info['discriminator']}\n" +
                 f"ID: {user_info['id']}\n" +
                 f"Bot: {user_info['bot']}\n" +
                 f"Created: {user_info['created_at']}"
        )]

    elif name == "moderate_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        # Delete the message
        await message.delete(reason=arguments["reason"])
        
        # Handle timeout if specified
        if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
            if isinstance(message.author, discord.Member):
                duration = discord.utils.utcnow() + datetime.timedelta(
                    minutes=arguments["timeout_minutes"]
                )
                await message.author.timeout(
                    duration,
                    reason=arguments["reason"]
                )
                return [TextContent(
                    type="text",
                    text=f"Message deleted and user timed out for {arguments['timeout_minutes']} minutes."
                )]
        
        return [TextContent(
            type="text",
            text="Message deleted successfully."
        )]

    # Server Information Tools
    elif name == "get_server_info":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        info = {
            "name": guild.name,
            "id": str(guild.id),
            "owner_id": str(guild.owner_id),
            "member_count": guild.member_count,
            "created_at": guild.created_at.isoformat(),
            "description": guild.description,
            "premium_tier": guild.premium_tier,
            "explicit_content_filter": str(guild.explicit_content_filter)
        }
        return [TextContent(
            type="text",
            text=f"Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
        )]

    elif name == "list_members":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        limit = min(int(arguments.get("limit", 100)), 1000)
        
        members = []
        async for member in guild.fetch_members(limit=limit):
            members.append({
                "id": str(member.id),
                "name": member.name,
                "nick": member.nick,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "roles": [str(role.id) for role in member.roles[1:]]  # Skip @everyone
            })
        
        return [TextContent(
            type="text",
            text=f"Server Members ({len(members)}):\n" + 
                 "\n".join(f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})" for m in members)
        )]
    elif name == "list_servers":
        servers = []
        for guild in discord_client.guilds:
            servers.append({
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
                "created_at": guild.created_at.isoformat()
            })
        
        return [TextContent(
            type="text",
            text=f"Available Servers ({len(servers)}):\n" + 
                "\n".join(f"{s['name']} (ID: {s['id']}, Members: {s['member_count']})" for s in servers)
        )]

    # Role Management Tools
    elif name == "add_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.add_roles(role, reason="Role added via MCP")
        return [TextContent(
            type="text",
            text=f"Added role {role.name} to user {member.name}"
        )]

    elif name == "remove_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.remove_roles(role, reason="Role removed via MCP")
        return [TextContent(
            type="text",
            text=f"Removed role {role.name} from user {member.name}"
        )]

    # Channel Management Tools
    elif name == "create_text_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        category = None
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
        
        channel = await guild.create_text_channel(
            name=arguments["name"],
            category=category,
            topic=arguments.get("topic"),
            reason="Channel created via MCP"
        )
        
        return [TextContent(
            type="text",
            text=f"Created text channel #{channel.name} (ID: {channel.id})"
        )]

    elif name == "delete_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        await channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
        return [TextContent(
            type="text",
            text=f"Deleted channel successfully"
        )]

    # Message Reaction Tools
    elif name == "add_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.add_reaction(arguments["emoji"])
        return [TextContent(
            type="text",
            text=f"Added reaction {arguments['emoji']} to message"
        )]

    elif name == "add_multiple_reactions":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        for emoji in arguments["emojis"]:
            await message.add_reaction(emoji)
        return [TextContent(
            type="text",
            text=f"Added reactions: {', '.join(arguments['emojis'])} to message"
        )]

    elif name == "remove_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.remove_reaction(arguments["emoji"], discord_client.user)
        return [TextContent(
            type="text",
            text=f"Removed reaction {arguments['emoji']} from message"
        )]
    
    # DM Tools
    elif name == "send_dm":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        dm_channel = await user.create_dm()
        
        # Prepare kwargs for message sending
        kwargs = {}
        if "content" in arguments:
            kwargs["content"] = arguments["content"]
        
        # Handle embeds if provided
        if "embeds" in arguments and arguments["embeds"]:
            embeds = []
            for embed_data in arguments["embeds"]:
                embed = discord.Embed()
                
                # Set basic embed properties
                if "title" in embed_data:
                    embed.title = embed_data["title"]
                if "description" in embed_data:
                    embed.description = embed_data["description"]
                if "url" in embed_data:
                    embed.url = embed_data["url"]
                if "color" in embed_data:
                    embed.color = embed_data["color"]
                if "timestamp" in embed_data and embed_data["timestamp"]:
                    embed.timestamp = datetime.fromisoformat(embed_data["timestamp"])
                
                # Set author if provided
                if "author" in embed_data:
                    name = embed_data["author"].get("name", "")
                    url = embed_data["author"].get("url", None)
                    icon_url = embed_data["author"].get("icon_url", None)
                    embed.set_author(name=name, url=url, icon_url=icon_url)
                
                # Set footer if provided
                if "footer" in embed_data:
                    text = embed_data["footer"].get("text", "")
                    icon_url = embed_data["footer"].get("icon_url", None)
                    embed.set_footer(text=text, icon_url=icon_url)
                
                # Set thumbnail if provided
                if "thumbnail" in embed_data and "url" in embed_data["thumbnail"]:
                    embed.set_thumbnail(url=embed_data["thumbnail"]["url"])
                
                # Set image if provided
                if "image" in embed_data and "url" in embed_data["image"]:
                    embed.set_image(url=embed_data["image"]["url"])
                
                # Add fields if provided
                if "fields" in embed_data:
                    for field in embed_data["fields"]:
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False)
                        )
                
                embeds.append(embed)
            
            kwargs["embeds"] = embeds
        
        try:
            message = await dm_channel.send(**kwargs)
            return [TextContent(
                type="text",
                text=f"DM sent successfully to {user.name}. Message ID: {message.id}"
            )]
        except discord.errors.Forbidden as e:
            if e.code == 50007:
                return [TextContent(
                    type="text",
                    text=f"Error: Cannot send DM to {user.name}. Possible reasons:\n"
                         f"1. The user has blocked the bot\n"
                         f"2. The user has their privacy settings set to not receive DMs from non-friends\n"
                         f"3. The bot doesn't share a mutual server with this user\n\n"
                         f"Solution: Make sure the bot and user share a server and that the user's privacy settings "
                         f"allow DMs from server members."
                )]
            else:
                raise
    
    elif name == "dm_conversation":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        dm_channel = await user.create_dm()
        timeout = int(arguments.get("timeout", 60))
        
        # Prepare kwargs for message sending
        kwargs = {}
        if "content" in arguments:
            kwargs["content"] = arguments["content"]
        
        # Handle embeds if provided
        if "embeds" in arguments and arguments["embeds"]:
            embeds = []
            for embed_data in arguments["embeds"]:
                embed = discord.Embed()
                
                # Set basic embed properties
                if "title" in embed_data:
                    embed.title = embed_data["title"]
                if "description" in embed_data:
                    embed.description = embed_data["description"]
                if "url" in embed_data:
                    embed.url = embed_data["url"]
                if "color" in embed_data:
                    embed.color = embed_data["color"]
                if "timestamp" in embed_data and embed_data["timestamp"]:
                    embed.timestamp = datetime.fromisoformat(embed_data["timestamp"])
                
                # Set author if provided
                if "author" in embed_data:
                    name = embed_data["author"].get("name", "")
                    url = embed_data["author"].get("url", None)
                    icon_url = embed_data["author"].get("icon_url", None)
                    embed.set_author(name=name, url=url, icon_url=icon_url)
                
                # Set footer if provided
                if "footer" in embed_data:
                    text = embed_data["footer"].get("text", "")
                    icon_url = embed_data["footer"].get("icon_url", None)
                    embed.set_footer(text=text, icon_url=icon_url)
                
                # Set thumbnail if provided
                if "thumbnail" in embed_data and "url" in embed_data["thumbnail"]:
                    embed.set_thumbnail(url=embed_data["thumbnail"]["url"])
                
                # Set image if provided
                if "image" in embed_data and "url" in embed_data["image"]:
                    embed.set_image(url=embed_data["image"]["url"])
                
                # Add fields if provided
                if "fields" in embed_data:
                    for field in embed_data["fields"]:
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False)
                        )
                
                embeds.append(embed)
            
            kwargs["embeds"] = embeds
        
        try:
            # Send the message
            sent_message = await dm_channel.send(**kwargs)
            
            # Define a check function to filter messages
            def check(message):
                return message.author.id == int(arguments["user_id"]) and message.channel.id == dm_channel.id
            
            try:
                # Wait for the response with timeout
                response = await discord_client.wait_for('message', check=check, timeout=timeout)
                
                # Prepare the sent message content for display
                sent_content = sent_message.content if sent_message.content else "Embed message"
                
                return [TextContent(
                    type="text",
                    text=(f"DM conversation with {user.name}:\n"
                         f"Bot: {sent_content}\n"
                         f"{user.name}: {response.content}\n"
                         f"Response received at: {response.created_at.isoformat()}")
                )]
            except asyncio.TimeoutError:
                return [TextContent(
                    type="text",
                    text=f"DM sent to {user.name}, but they did not respond within {timeout} seconds."
                )]
        except discord.errors.Forbidden as e:
            if e.code == 50007:
                return [TextContent(
                    type="text",
                    text=f"Error: Cannot send DM to {user.name}. Possible reasons:\n"
                         f"1. The user has blocked the bot\n"
                         f"2. The user has their privacy settings set to not receive DMs from non-friends\n"
                         f"3. The bot doesn't share a mutual server with this user\n\n"
                         f"Solution: Make sure the bot and user share a server and that the user's privacy settings "
                         f"allow DMs from server members."
                )]
            else:
                raise

    raise ValueError(f"Unknown tool: {name}")

async def main():
    # Start Discord bot in the background
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

