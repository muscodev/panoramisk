import asyncio
from panoramisk.fastagi_extension import FastAgi,Request



app = FastAgi()

@app.route('/hello')
async def hello(request: Request):

    await request.send_command('hello World')

async def main():
    server = await app.start_server()
    print("server started")
    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Close the server
        server.close()
    

if __name__ == '__main__':
    asyncio.run(main())
