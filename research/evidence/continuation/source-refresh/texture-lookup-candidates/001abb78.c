
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/entity/people/driver/ai/behave/bh_highl.c:1390 */

undefined8 FUN_001abb78(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  uint uVar1;
  int iVar2;
  long lVar3;
  undefined8 uVar4;
  int *piVar5;
  float fVar6;
  
  piVar5 = (int *)param_1;
  iVar2 = *(int *)(*(int *)(piVar5[1] + 0x14c) + 0x18c);
  lVar3 = FUN_001ac2d0(0xbf800000,param_1,param_3);
  if (lVar3 == 0) {
    uVar1 = *(uint *)(iVar2 + 0x28);
    if (uVar1 != 2) {
      if (uVar1 < 3) {
        if (uVar1 != 1) {
LAB_001abcc4:
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x262f18,0x56e,0x262f78);
        }
      }
      else if (uVar1 != 3) goto LAB_001abcc4;
    }
    uVar4 = FUN_001ab7c8(param_1,param_2,param_3);
    FUN_001a3240(param_1,9);
  }
  else {
    fVar6 = *(float *)(piVar5[1] + 0xec);
    iVar2 = (int)param_3;
    *(undefined4 *)(iVar2 + 0x1c) = *(undefined4 *)(piVar5[1] + 0x114);
    *(undefined4 *)(iVar2 + 0x28) = 1;
    *(undefined4 *)(iVar2 + 0x34) = 3;
    *(undefined4 *)(iVar2 + 0x30) = 2;
    *(undefined4 *)(iVar2 + 0x2c) = 0xd;
    *(undefined4 *)(iVar2 + 0x14) = 0;
    FUN_001a3240(param_1,10);
    if (fVar6 < 10.0) {
      iVar2 = (**(code **)(&DAT_0023cf9c + *piVar5 * 0x5c))(param_1,3);
      FUN_001cb938(*(undefined4 *)(piVar5[1] + 0xe0),0);
      *(undefined4 *)(*(int *)(iVar2 + 4) + 0x30) = 4;
      uVar4 = 1;
    }
    else {
      uVar4 = 1;
    }
  }
  return uVar4;
}

