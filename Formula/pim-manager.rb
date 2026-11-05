class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.0/pim-manager_0.4.0_darwin_arm64.tar.gz"
      sha256 "f86dab118d53ea057ee5f54299396f7d0260660c33e4aee9d41640912860d769"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.0/pim-manager_0.4.0_darwin_amd64.tar.gz"
      sha256 "8af77990e13cc686821c76ad0af1c2d22036e2b7f8d19e3d0811dd291933d465"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.0/pim-manager_0.4.0_linux_arm64.tar.gz"
      sha256 "b75f3c1420eb6bcf32633e12aa91eeec70a48c87f62dd50cc35fa52cb1a6095a"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.0/pim-manager_0.4.0_linux_amd64.tar.gz"
      sha256 "1ff9e423d3cb1f7e4a83d70f4a4865ac77c7d5436224d1d570aec9192edec3fe"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
