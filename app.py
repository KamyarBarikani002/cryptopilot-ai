from config.settings import PROJECT_NAME
from src.core.pipeline import CryptoPilotPipeline


print("=" * 40)
print(PROJECT_NAME)
print("=" * 40)


engine = CryptoPilotPipeline()

engine.run()
