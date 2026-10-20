class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.2.0/pim-manager_0.2.0_darwin_arm64.tar.gz"
      sha256 "7f2b4da4c4b33a6375f673e50665b65c1f37b778407c260d7ff40b2b50eacb5f"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.2.0/pim-manager_0.2.0_darwin_amd64.tar.gz"
      sha256 "65385c0511da3313d3469a257878a8fa0abc91d2a60d4cc7b08c48f028732d71"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.2.0/pim-manager_0.2.0_linux_arm64.tar.gz"
      sha256 "1a02dab5df372e63950dadfe491b1cb64179f65f4104400640e00a7fd56d20b7"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.2.0/pim-manager_0.2.0_linux_amd64.tar.gz"
      sha256 "583cc7dfcda31e5f5ce840e65ec7aee82e5057a02e980c153fbb18264ae91ac5"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
