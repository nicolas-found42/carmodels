
/* WARNING: Removing unreachable block (ram,0x00125e40) */

void FUN_00125dc8(int param_1)

{
  ushort uVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int iVar5;
  uint *puVar6;
  int iVar7;
  int iVar8;
  uint uVar9;
  int *piVar10;
  int iVar11;
  
  iVar4 = FUN_0021b6e0(*(undefined4 *)(param_1 + 4));
  iVar5 = FUN_001213d8(*(undefined4 *)(param_1 + 4));
  uVar1 = *(ushort *)(param_1 + 100);
  uVar9 = (uint)*(byte *)(iVar5 + 0xe);
  iVar11 = 0;
  if (uVar9 != 0) {
    iVar2 = *(int *)(iVar4 + 0xf4);
    piVar10 = *(int **)(iVar5 + 0x1c);
    do {
      iVar3 = *piVar10;
      puVar6 = (uint *)(iVar3 * 8 + iVar2);
      if (((*puVar6 & 0x1000) != 0) && (*(char *)((int)puVar6 + 2) != '\0')) {
        iVar8 = 0;
        if (*(byte *)((int)puVar6 + 3) == uVar1) {
          iVar8 = *(int *)(iVar4 + 0xec);
          uVar9 = puVar6[1];
        }
        else {
          do {
            iVar8 = iVar8 + 1;
            iVar7 = (iVar3 + iVar8) * 8 + iVar2;
            if ((int)(uint)*(byte *)(iVar3 * 8 + iVar2 + 2) < iVar8) goto LAB_00125eac;
          } while (*(byte *)(iVar7 + 3) != uVar1);
          iVar8 = *(int *)(iVar4 + 0xec);
          uVar9 = *(uint *)(iVar7 + 4);
        }
        *(uint *)(iVar3 * 4 + iVar8) = uVar9;
        uVar9 = (uint)*(byte *)(iVar5 + 0xe);
      }
LAB_00125eac:
      iVar11 = iVar11 + 1;
      piVar10 = piVar10 + 1;
    } while (iVar11 < (int)uVar9);
  }
  return;
}

