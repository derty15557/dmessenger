# simple_server.py
import asyncio
import websockets

async def handler(websocket, path):
    async for message in websocket:
        await websocket.send(f"Echo: {message}")

async def main():
    print("🟢 Запуск сервера...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("🟢 Сервер запущен на ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())