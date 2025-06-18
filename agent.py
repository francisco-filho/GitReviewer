import os
import json
import uuid
import time
import git
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --- Tools ---
def diff_tool(project_dir: str, only_staged: bool = True) -> str:
    """
    Executes a diff in the changes made in the repository.

    Parameters:
        project_dir: Directory of the project with a git repo.
        only_staged: If true, diff only staged files.
    Returns:
        The diff output as a string.
    """
    if not os.path.isdir(project_dir):
        return f"Error: Project directory '{project_dir}' does not exist."
    try:
        repo = git.Repo(project_dir)
        if only_staged:
            # Use diff_cached for staged changes
            diff_output = repo.git.diff(cached=True)
        else:
            # Diff between working tree and index (unstaged changes) + staged changes
            diff_output = repo.git.diff() + "\n" + repo.git.diff(cached=True)
        return diff_output
    except git.InvalidGitRepositoryError:
        return f"Error: '{project_dir}' is not a valid Git repository."
    except Exception as e:
        return f"An error occurred while getting diff: {e}"

# --- Memory ---
class Memory:
    """
    Responsible for storing prompts and messages in the interactions.
    Evicts older messages if 'max_interactions' is reached.
    """
    user_prompt: str
    plan: Union[str, None]
    interactions: List[Dict[str, str]]
    max_interactions: int

    def __init__(self, user_prompt: str, max_interactions: int = 24):
        self.user_prompt = user_prompt
        self.plan = None
        self.interactions = []
        self.max_interactions = max_interactions
        print(f"Memory initialized for prompt: '{user_prompt}'")

    def add_interaction(self, role: str, message: str):
        """Adds an interaction (system or user message) to memory."""
        if len(self.interactions) >= self.max_interactions:
            # Evict the oldest message if max interactions reached
            self.interactions.pop(0)
            print("Memory: Evicted oldest interaction.")
        self.interactions.append({"role": role, "message": message})
        print(f"Memory: Added {role} interaction. Current size: {len(self.interactions)}")

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Returns the current chat history formatted for LLM (user/model roles)."""
        history = []
        for interaction in self.interactions:
            # Map roles to 'user'/'model' for LLM consumption
            if interaction["role"] == "user":
                history.append({"role": "user", "parts": [interaction["message"]]}) # genai expects list of strings
            elif interaction["role"] == "agent_response":
                history.append({"role": "model", "parts": [interaction["message"]]})
            # Add any other roles if necessary
        return history

# --- Task ---
class Task(BaseModel):
    task: str
    needs_plan: bool = False
    needs_approval: bool = True
    context: Dict[str, Any] = Field(default_factory=dict)

# --- LLM Client ---
class LLMClient(ABC):
    @abstractmethod
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        """
        Abstract method for chatting with an LLM.
        Returns the content of the LLM's response.
        """
        pass

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-preview-05-20"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_key = api_key
        #genai.configure(api_key=self.api_key)
        self.model = genai.Client()
        print(f"GeminiClient initialized for model: {self.model_name}")

    def chat(self, prompt: str, system_prompt: str = "") -> str:
        """
        Sends a chat prompt to the Gemini API and returns the response.
        """
        print(f"\n--- Calling Gemini LLM ({self.model_name}) ---")
        print(f"Prompt: {prompt[:100]}...") # Print first 100 chars
        if system_prompt:
            print(f"System Prompt: {system_prompt[:100]}...")

        try:
            # Create a chat session to handle multi-turn conversations if needed
            # For a single turn, just using model.generate_content is sufficient
            # However, for system_prompt, it's often better handled as part of the prompt
            # or by fine-tuning the model.

            # For simplicity, we'll use generate_content directly.
            # If `system_prompt` is provided, prepend it to the `prompt`.
            full_prompt_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            generation_config = types.GenerateContentConfig(
                response_mime_type="text/plain"
            )

            #resp = self.client.models.generate_content(
            response = self.model.models.generate_content(
                contents=full_prompt_text,
                model=self.model_name,
                config=generation_config
            )

            if response.candidates and len(response.candidates) > 0 and response.candidates[0].content:
                text = response.candidates[0].content.parts[0].text
                print(f"LLM Response: {text[:100]}...") # Print first 100 chars
                return text
            else:
                print(f"Error: Unexpected LLM response structure: {response}")
                return "Error: Could not get a valid response from the LLM."

        except Exception as e:
            print(f"An unexpected error occurred during LLM chat: {e}")
            return f"Error: An unexpected error occurred: {e}"

# --- Agent Base Class ---
class Agent(ABC):
    def __init__(self, name: str, llm_client: LLMClient, description: str, system_prompt: str, tools: list):
        self.name = name
        self.llm_client = llm_client
        self.description = description
        self.system_prompt = system_prompt
        self.tools = tools # List of callable functions

    @abstractmethod
    def run(self, **kwargs) -> str:
        """
        Abstract method to run the agent's task.
        Kwargs can include 'prompt', 'diff', etc., depending on the agent's needs.
        Returns the agent's response as a string.
        """
        pass

# --- Specific Agents ---
class Commiter(Agent):
    def __init__(self, llm_client: LLMClient, system_prompt: str, tools: list):
        super().__init__(
            name="Commiter",
            llm_client=llm_client,
            description="Generates concise and descriptive commit messages based on code changes (diff).",
            system_prompt=system_prompt,
            tools=tools
        )

    def run(self, prompt: str, diff: str) -> str:
        """
        Generates a commit message using the LLM based on the provided diff.

        Parameters:
            prompt: The user's original request or current instruction.
            diff: The git diff output to analyze.
        Returns:
            The generated commit message.
        """
        print(f"--- Running Commiter Agent ---")
        full_prompt = f"User request: '{prompt}'\n\nCode changes (diff):\n```diff\n{diff}\n```\n\nGenerate a concise and descriptive commit message for these changes."
        response = self.llm_client.chat(full_prompt, self.system_prompt)
        return response

class Evaluator(Agent):
    def __init__(self, llm_client: LLMClient, system_prompt: str, tools: list):
        super().__init__(
            name="Evaluator",
            llm_client=llm_client,
            description="Evaluates the quality of commit messages based on provided code diffs. Responds with 'Commit message accepted' or 'Bad commit message' and a reason.",
            system_prompt=system_prompt,
            tools=tools
        )

    def run(self, commit_message: str, diff: str) -> str:
        """
        Evaluates a commit message based on the provided diff.

        Parameters:
            commit_message: The commit message to evaluate.
            diff: The git diff output to analyze.
        Returns:
            "Commit message accepted" or "Bad commit message" with a reason.
        """
        print(f"--- Running Evaluator Agent ---")
        full_prompt = (
            f"Review the following commit message and the associated code changes (diff).\n\n"
            f"Commit Message:\n```\n{commit_message}\n```\n\n"
            f"Code Changes (diff):\n```diff\n{diff}\n```\n\n"
            f"If the commit message is good, respond with 'Commit message accepted'.\n"
            f"If it's bad, respond with 'Bad commit message', followed by two new lines, and then the reason why it's bad."
        )
        response = self.llm_client.chat(full_prompt, self.system_prompt)
        return response

# --- LegionAI Orchestrator ---
class LegionAI:
    """
    Responsible for selecting and orchestrating the execution of tasks.
    """
    available_agents: List[Agent] = []
    memory: Memory
    llm_client: LLMClient

    def __init__(self, memory: Memory, llm_client: LLMClient):
        self.memory = memory
        self.llm_client = llm_client
        print("LegionAI orchestrator initialized.")

    def add(self, agent: Agent):
        """Adds an agent to the list of available agents."""
        self.available_agents.append(agent)
        print(f"Added agent: {agent.name}")

    def _select_agent(self, task_description: str) -> Union[Agent, None]:
        """
        Uses the LLM to select the most appropriate agent for the given task.
        """
        if not self.available_agents:
            print("No agents available for selection.")
            return None

        agent_info = "\n".join([f"- {agent.name}: {agent.description}" for agent in self.available_agents])
        selection_prompt = (
            f"The user wants to perform the following task:\n'{task_description}'\n\n"
            f"Here are the available agents and their descriptions:\n{agent_info}\n\n"
            f"Based on the task description, which agent is the most appropriate to handle this task? "
            f"Respond with only the name of the agent (e.g., 'Commiter', 'Evaluator'). "
            f"If no agent is suitable, respond with 'None'."
        )

        print("\n--- Agent Selection ---")
        agent_name = self.llm_client.chat(selection_prompt).strip()
        print(f"LLM selected agent: '{agent_name}'")

        for agent in self.available_agents:
            if agent.name.lower() == agent_name.lower():
                return agent
        print(f"Warning: Selected agent '{agent_name}' not found in available agents.")
        return None

    def run(self, task: Task, max_attempts: int = 3):
        """
        Executes the given task by selecting and orchestrating the appropriate agent.

        Parameters:
            task: The Task object to execute.
            max_attempts: Maximum number of attempts for an agent to complete the task.
        """
        print(f"\n--- LegionAI: Starting task '{task.task}' ---")
        self.memory.add_interaction("system", f"Starting task: {task.task}")
        self.memory.user_prompt = task.task # Ensure user_prompt in memory is set

        selected_agent = self._select_agent(task.task)

        if not selected_agent:
            print(f"Task '{task.task}' could not be fulfilled: No appropriate agent found.")
            self.memory.add_interaction("system", "No appropriate agent found for the task.")
            return

        print(f"LegionAI: Selected agent '{selected_agent.name}' for the task.")
        self.memory.add_interaction("system", f"Selected agent: {selected_agent.name}")

        attempts = 0
        current_prompt = task.task
        agent_response = ""

        while attempts < max_attempts:
            attempts += 1
            print(f"\n--- Attempt {attempts}/{max_attempts} ---")

            if task.needs_plan and self.memory.plan is None:
                # Generate a plan if needed and not already generated
                plan_prompt = f"Create a step-by-step plan to achieve the following task: '{current_prompt}'. Be concise."
                self.memory.plan = self.llm_client.chat(plan_prompt, "You are a helpful assistant that generates plans.")
                print(f"LegionAI: Generated plan: {self.memory.plan}")
                self.memory.add_interaction("system", f"Plan generated: {self.memory.plan}")

            # Prepare arguments for the agent's run method
            # This needs to be dynamic based on the agent's expected kwargs
            agent_kwargs = {"prompt": current_prompt}

            # For Commiter, we need the diff
            if selected_agent.name == "Commiter":
                project_dir = task.context.get("project_dir")
                if not project_dir:
                    print("Error: 'project_dir' not provided in task context for Commiter agent.")
                    self.memory.add_interaction("system", "Error: Missing project directory for Commiter agent.")
                    return
                diff_output = diff_tool(project_dir)
                if "Error:" in diff_output:
                    print(f"Error executing diff_tool: {diff_output}")
                    self.memory.add_interaction("system", f"Error executing diff_tool: {diff_output}")
                    return
                agent_kwargs["diff"] = diff_output
                print(f"LegionAI: Passed diff to Commiter agent. Diff length: {len(diff_output)} chars.")

            # For Evaluator, we need the commit message and diff.
            # This implies a multi-step workflow, which the current `run` design
            # needs to explicitly manage (e.g., if Commiter generates, then Evaluator evaluates).
            # For this example, let's assume the prompt for Evaluator directly includes the commit message.
            # A more robust system would involve state passing between agents or a sub-orchestrator.
            if selected_agent.name == "Evaluator":
                # For demonstration, let's assume the previous agent_response (commit message) is passed here
                # In a real scenario, LegionAI would track the output of previous steps.
                if not agent_response: # If agent_response is empty, it means Commiter hasn't run yet or failed
                    print("Error: Evaluator agent requires a commit message to evaluate. No previous agent response found.")
                    self.memory.add_interaction("system", "Error: Evaluator requires a commit message.")
                    return

                project_dir = task.context.get("project_dir")
                if not project_dir:
                    print("Error: 'project_dir' not provided in task context for Evaluator agent.")
                    self.memory.add_interaction("system", "Error: Missing project directory for Evaluator agent.")
                    return
                diff_output = diff_tool(project_dir)
                if "Error:" in diff_output:
                    print(f"Error executing diff_tool: {diff_output}")
                    self.memory.add_interaction("system", f"Error executing diff_tool: {diff_output}")
                    return

                agent_kwargs["commit_message"] = agent_response # The response from the Commiter agent
                agent_kwargs["diff"] = diff_output
                print(f"LegionAI: Passed commit message and diff to Evaluator agent.")

            try:
                agent_response = selected_agent.run(**agent_kwargs)
                self.memory.add_interaction("agent_response", agent_response)
                print(f"Agent '{selected_agent.name}' response:\n{agent_response}")

                if task.needs_approval:
                    while True:
                        user_input = input("\nIs this task completed? (y/n): ").lower().strip()
                        if user_input == 'y':
                            print("Task approved by user. Completing task.")
                            self.memory.add_interaction("user", "User approved task completion.")
                            return
                        elif user_input == 'n':
                            rejection_reason = input("Please explain why it's not completed: ").strip()
                            current_prompt = f"The previous attempt was not satisfactory. Reason for rejection: {rejection_reason}. Please try again, incorporating this feedback: {task.task}"
                            self.memory.add_interaction("user", f"User rejected: {rejection_reason}")
                            print("Task rejected by user. Re-attempting...")
                            break # Break from inner loop to retry
                        else:
                            print("Invalid input. Please enter 'y' or 'n'.")
                else:
                    # If no approval is needed, check specific agent completion criteria
                    if selected_agent.name == "Evaluator":
                        if "commit message accepted" in agent_response.lower():
                            print("Evaluator accepted the commit message. Task considered complete.")
                            self.memory.add_interaction("system", "Evaluator accepted the commit message.")
                            return
                        else:
                            print("Evaluator rejected the commit message. Re-attempting Commiter if possible.")
                            self.memory.add_interaction("system", "Evaluator rejected the commit message.")
                            # If Evaluator rejects, we need to prompt the Commiter again with the feedback
                            # This requires a more complex state machine for multi-agent workflows.
                            # For simplicity, we'll loop the *current* agent unless the agent is Commiter and it's rejected.
                            # In a real system, the orchestrator would redirect to the Commiter again.
                            # For this example, let's just update the prompt for the *current* agent.
                            current_prompt = f"The previous result was rejected. Feedback: {agent_response}. Please revise and try again: {task.task}"
                            if selected_agent.name == "Commiter":
                                # If the commiter produced a bad message, the evaluator would have flagged it
                                # and the feedback would be used to retry the commiter.
                                pass
                            else:
                                # For other agents, if no approval, they are considered done after one run
                                # unless the response indicates failure.
                                print("Agent completed without requiring explicit approval.")
                                return # Task is considered complete by agent itself

            except Exception as e:
                print(f"Error during agent '{selected_agent.name}' execution: {e}")
                self.memory.add_interaction("system", f"Error during agent execution: {e}")
                current_prompt = f"An error occurred during the last attempt: {e}. Please try again: {task.task}"
                time.sleep(1) # Small delay before retrying

        print(f"\n--- LegionAI: Max attempts ({max_attempts}) reached for task '{task.task}'. Task incomplete. ---")
        self.memory.add_interaction("system", "Max attempts reached. Task incomplete.")

# --- Main Execution ---
if __name__ == "__main__":
    # Ensure you have a test Git repository for diff_tool
    # For example:
    # 1. mkdir /tmp/test_project
    # 2. cd /tmp/test_project
    # 3. git init
    # 4. echo "hello world" > test.txt
    # 5. git add test.txt
    # 6. git commit -m "initial commit"
    # 7. echo "updated content" > test.txt
    # 8. git add test.txt (this will make it staged for diff_tool)

    # Initialize LLM Client
    # Ensure GEMINI_API_KEY is set as an environment variable or replaced directly
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # Initialize the LLMClient outside the agents so it can be shared.
    gemini_llm_client = GeminiClient(api_key=GEMINI_API_KEY)

    # Create an instance of Memory
    # The actual user prompt will be set by LegionAI.run, but we need an initial object.
    temp_memory = Memory(user_prompt="Initial prompt placeholder", max_interactions=24)

    # Instantiate Agents
    commiter_agent = Commiter(
        llm_client=gemini_llm_client,
        system_prompt="You are a senior programmer that explains hard concepts clearly and are very succinctly in your messages. You can evaluate changes in a project just by reading the diff output from git.",
        tools=[diff_tool]
    )

    evaluator_agent = Evaluator(
        llm_client=gemini_llm_client,
        system_prompt="""
        You are a senior programmer that has attention to details and likes very clear texts. You make code reviews and evaluate the quality of commit messages based on the diff changes.
        If your evaluation is positive, just respond with 'Commit message accepted', but
        if the commit message has any problems respond with 'Bad commit message', two new lines and the motive.
        """,
        tools=[diff_tool]
    )

    # Create LegionAI instance
    legion = LegionAI(memory=temp_memory, llm_client=gemini_llm_client)
    legion.add(commiter_agent)
    legion.add(evaluator_agent)

    # --- Example Task 1: Generate a commit message ---
    print("\n" + "="*50)
    print("Executing Task 1: Generate a commit message")
    print("="*50 + "\n")
    project_directory_for_task = '/home/wsl/desenv/ai/GitReviewer' # Make sure this directory exists and is a git repo
    task1 = Task(
        task=f"Generate a concise commit message for the currently staged changes in the project located at '{project_directory_for_task}'.",
        needs_approval=True,
        context={"project_dir": project_directory_for_task}
    )
    legion.run(task1, max_attempts=2) # Reduced attempts for faster testing

    print("\n" + "="*50)
    print("Task 1 Completed/Aborted. Memory interactions:")
    for i, interaction in enumerate(temp_memory.interactions):
        print(f"  {i+1}. [{interaction['role']}]: {interaction['message']}")
    print("="*50 + "\n")

    # --- Example Task 2: Evaluate a commit message (simulated) ---
    # This requires the Commiter to have run first to produce a message.
    # For a direct example, we'll simulate the commit message output.
    print("\n" + "="*50)
    print("Executing Task 2: Evaluate a simulated commit message")
    print("="*50 + "\n")

    # Reset memory for the new task
    temp_memory = Memory(user_prompt="Evaluate a commit message placeholder", max_interactions=24)
    legion.memory = temp_memory # Update LegionAI's memory reference

    simulated_commit_message = "feat: Add user authentication. This commit introduces user authentication features including signup, login, and password reset functionalities."

    task2 = Task(
        task=f"Evaluate the following commit message based on the staged changes in '{project_directory_for_task}': '{simulated_commit_message}'",
        needs_approval=False, # Evaluator decides, no direct user approval
        context={"project_dir": project_directory_for_task}
    )

    # For Task 2, we explicitly set the 'agent_response' in memory as if it came from a previous Commiter run
    # This is a simplification for demonstration. In a real system, LegionAI would manage the flow
    # from Commiter output -> Evaluator input.
    temp_memory.add_interaction("agent_response", simulated_commit_message)

    legion.run(task2, max_attempts=1) # Evaluator should ideally run once

    print("\n" + "="*50)
    print("Task 2 Completed/Aborted. Memory interactions:")
    for i, interaction in enumerate(temp_memory.interactions):
        print(f"  {i+1}. [{interaction['role']}]: {interaction['message']}")
    print("="*50 + "\n")

