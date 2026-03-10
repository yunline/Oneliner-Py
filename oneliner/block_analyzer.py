from ast import *

class Block:
    context: FunctionDef | ClassDef | Module
    body: list[stmt]

class SimpleBlock(Block):
    pass

class JumpEndingBlock(Block):
    ending_node: Continue | Break

class ReturnEndingBlock(Block):
    ending_node: Return 

class BranchEndingBlock(Block):
    ending_node: If
    inner_body_blocks: list[Block]
    inner_orelse_blocks: list[Block]

class LoopEndingBlock(Block):
    ending_node: While | For
    inner_body_blocks: list[Block]
    inner_orelse_blocks: list[Block]


def analyze_blocks(root: Module) -> dict[Module | FunctionDef | ClassDef, list[Block]]:
    results: dict[Module | FunctionDef | ClassDef, list[Block]] = {}

    scope_stack: list[Module | FunctionDef | ClassDef] = []
    scope_stack.append(root)

    def generate_blocks(body: list[stmt]) -> list[Block]:
        block_body: list[stmt] = []
        result: list[Block] = []
        for node in body:

            if isinstance(node, (FunctionDef, ClassDef)):
                scope_stack.append(node)

            block: Block
            if isinstance(node, If):
                block = BranchEndingBlock()
                block.ending_node = node
                block.body = block_body
                block_body = []
                result.append(block)
            elif isinstance(node, (While, For)):
                block = LoopEndingBlock()
                block.ending_node = node
                block.body = block_body
                block_body = []
                result.append(block)
            elif isinstance(node, (Continue, Break)):
                block = JumpEndingBlock()
                block.ending_node = node
                block.body = block_body
                block_body = []
                result.append(block)
                break
            elif isinstance(node, Return):
                block = ReturnEndingBlock()
                block.ending_node = node
                block.body = block_body
                block_body = []
                result.append(block)
                break
            else:
                block_body.append(node)
            
        ending_block = SimpleBlock()
        ending_block.body = block_body
        result.append(ending_block)

        return result

    def finallize_block(block: Block):
        finallizing_stack = [block]
        while finallizing_stack:
            current_block = finallizing_stack.pop()
            if isinstance(current_block, (SimpleBlock, JumpEndingBlock, ReturnEndingBlock)):
                continue
            assert isinstance(current_block, (BranchEndingBlock, LoopEndingBlock))
            
            body_blocks = generate_blocks(current_block.ending_node.body)
            orelse_blocks = generate_blocks(current_block.ending_node.body)

            current_block.inner_body_blocks = body_blocks
            current_block.inner_orelse_blocks = orelse_blocks

            finallizing_stack.extend(body_blocks)
            finallizing_stack.extend(orelse_blocks)
        

    while scope_stack:
        current_scope = scope_stack.pop()
        blocks = generate_blocks(current_scope.body)
        results[current_scope] = blocks

        for block in blocks:
            finallize_block(block)

    return results

